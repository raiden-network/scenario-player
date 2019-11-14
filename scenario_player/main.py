from __future__ import annotations

import functools
import json
import os
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path

import click
import gevent
import structlog
from eth_utils import to_checksum_address
from urwid import ExitMainLoop
from web3.utils.transactions import TRANSACTION_DEFAULTS

from raiden.accounts import Account
from raiden.log_config import _FIRST_PARTY_PACKAGES, configure_logging
from raiden.utils.cli import EnumChoiceType
from scenario_player import __version__, tasks
from scenario_player.constants import DEFAULT_ETH_RPC_ADDRESS, DEFAULT_NETWORK
from scenario_player.exceptions import ScenarioAssertionError, ScenarioError
from scenario_player.exceptions.cli import WrongPassword
from scenario_player.exceptions.services import ServiceProcessException
from scenario_player.runner import ScenarioRunner
from scenario_player.services.common.app import ServiceProcess
from scenario_player.tasks.base import collect_tasks
from scenario_player.ui import ScenarioUI, attach_urwid_logbuffer
from scenario_player.utils import DummyStream, post_task_state_to_rc, send_notification_mail
from scenario_player.utils.legacy import MutuallyExclusiveOption
from scenario_player.utils.version import get_complete_spec

log = structlog.get_logger(__name__)

TRANSACTION_DEFAULTS["gas"] = lambda web3, tx: web3.eth.estimateGas(tx) * 2


class TaskNotifyType(Enum):
    NONE = "none"
    ROCKETCHAT = "rocket-chat"


def construct_log_file_name(sub_command, data_path, scenario_fpath: Path = None) -> str:
    directory = data_path
    if scenario_fpath:
        file_name = (
            f"scenario-player-{sub_command}_{scenario_fpath.stem}"
            f"_{datetime.now():%Y-%m-%dT%H:%M:%S}.log"
        )
        directory = directory.joinpath("scenarios", scenario_fpath.stem)
    else:
        file_name = f"scenario-player-{sub_command}_{datetime.now():%Y-%m-%dT%H:%M:%S}.log"
    return str(directory.joinpath(file_name))


def configure_logging_for_subcommand(log_file_name):
    Path(log_file_name).parent.mkdir(exist_ok=True, parents=True)
    click.secho(f"Writing log to {log_file_name}", fg="yellow")
    configure_logging(
        {"": "INFO", "raiden": "DEBUG", "scenario_player": "DEBUG"},
        debug_log_file_name=log_file_name,
        _first_party_packages=_FIRST_PARTY_PACKAGES | frozenset(["scenario_player"]),
        _debug_log_file_additional_level_filters={"scenario_player": "DEBUG"},
    )


def load_account_obj(keystore_file, password):
    with open(keystore_file, "r") as keystore:
        account = Account(json.load(keystore), password, keystore_file)
        log.info("Using account", account=to_checksum_address(account.address))
        return account


def get_password(password, password_file):
    if password_file:
        password = open(password_file, "r").read().strip()
    if password == password_file is None:
        password = click.prompt(text="Please enter your password: ", hide_input=True)
    return password


def get_account(keystore_file, password):
    try:
        account = load_account_obj(keystore_file, password)
    except ValueError:
        raise WrongPassword
    return account


def key_password_options(func):
    """Decorator for adding '--keystore-file', '--password/--password-file' to subcommands."""

    @click.option("--keystore-file", required=True, type=click.Path(exists=True, dir_okay=False))
    @click.option(
        "--password-file",
        type=click.Path(exists=True, dir_okay=False),
        cls=MutuallyExclusiveOption,
        mutually_exclusive=["password"],
        default=None,
    )
    @click.option(
        "--password",
        envvar="ACCOUNT_PASSWORD",
        cls=MutuallyExclusiveOption,
        mutually_exclusive=["password-file"],
        default=None,
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def data_path_option(func):
    """Decorator for adding '--data-path' to subcommands."""

    @click.option(
        "--data-path",
        default=Path(str(Path.home().joinpath(".raiden", "scenario-player"))),
        type=click.Path(exists=False, dir_okay=True, file_okay=False),
        show_default=True,
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def chain_option(func):
    """Decorator for adding '--chain' to subcommands."""

    @click.option(
        "--chain",
        "chain",
        multiple=False,
        required=False,
        help="Chain name to eth rpc url mapping.",
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@click.group(invoke_without_command=True, context_settings={"max_content_width": 120})
@click.pass_context
def main(ctx):
    gevent.get_hub().exception_stream = DummyStream()


@main.command(name="run")
@click.argument("scenario-file", type=click.File(), required=False)
@click.option("--auth", default="")
@click.option("--mailgun-api-key")
@click.option(
    "--notify-tasks",
    type=EnumChoiceType(TaskNotifyType),
    default=TaskNotifyType.NONE.value,
    help="Notify of task status via chosen method.",
)
@click.option(
    "--ui/--no-ui",
    "enable_ui",
    default=sys.stdout.isatty(),
    help="En-/disable console UI. [default: auto-detect]",
)
@key_password_options
@chain_option
@data_path_option
@click.pass_context
def run(
    ctx,
    chain,
    data_path,
    mailgun_api_key,
    auth,
    password,
    keystore_file,
    scenario_file,
    notify_tasks,
    enable_ui,
    password_file,
):
    """Execute a scenario as defined in scenario definition file.

    Calls :func:`exit` when done, with the following status codes:

        Exit code 1x
        There was a problem when starting up the SP, nodes, deploying tokens
        or setting up services. This points at an issue in the SP and of of its
        components.

        Exit code 2x
        There was an error when parsing or evaluating the given scenario definition file.
        This may be a syntax- or logic-related issue.

        Exit code 3x
        There was an assertion error while executing the scenario. This points
        to an error in a `raiden` component (the client, services or contracts).
    """
    data_path = Path(data_path)
    scenario_file = Path(scenario_file.name).absolute()
    log_file_name = construct_log_file_name("run", data_path, scenario_file)
    configure_logging_for_subcommand(log_file_name)
    log.info("Scenario Player version:", version_info=get_complete_spec())

    password = get_password(password, password_file)

    account = get_account(keystore_file, password)

    notify_tasks_callable = None
    if notify_tasks is TaskNotifyType.ROCKETCHAT:
        if "RC_WEBHOOK_URL" not in os.environ:
            click.secho(
                "'--notify-tasks rocket-chat' requires env variable 'RC_WEBHOOK_URL' to be set.",
                fg="red",
            )
        notify_tasks_callable = post_task_state_to_rc

    log_buffer = None

    # If the output is a terminal, beautify our output.
    if enable_ui:
        log_buffer = attach_urwid_logbuffer()

    # Dynamically import valid Task classes from sceanrio_player.tasks package.
    collect_tasks(tasks)

    # Start our Services
    service_process = ServiceProcess()

    service_process.start()

    # Run the scenario using the configurations passed.
    try:
        runner = ScenarioRunner(
            account, chain, auth, data_path, scenario_file, notify_tasks_callable
        )
    except Exception as e:
        # log anything that goes wrong during init of the runner and isn't handled.
        log.exception("Error during startup", exception=e)
        raise

    ui = None
    ui_greenlet = None
    if enable_ui:
        ui = ScenarioUI(runner, log_buffer, log_file_name)
        ui_greenlet = ui.run()
    success = False
    exit_code = 1
    subject = None
    message = None

    try:
        runner.run_scenario()
    except ScenarioAssertionError as ex:
        log.error("Run finished", result="assertion errors")
        if hasattr(ex, "exit_code"):
            exit_code = ex.exit_code
        else:
            exit_code = 30
        subject = f"Assertion mismatch in {scenario_file.name}"
        message = str(ex)
    except ScenarioError as ex:
        log.error("Run finished", result="scenario error")
        if hasattr(ex, "exit_code"):
            exit_code = ex.exit_code
        else:
            exit_code = 20
        subject = f"Invalid scenario {scenario_file.name}"
        message = traceback.format_exc()
    except Exception as ex:
        log.exception("Exception while running scenario")
        if hasattr(ex, "exit_code"):
            exit_code = ex.exit_code
        else:
            exit_code = 10
        subject = f"Error running scenario {scenario_file.name}"
        message = traceback.format_exc()
    else:
        success = True
        exit_code = 0
        log.info("Run finished", result="success")
        subject = f"Scenario successful {scenario_file.name}"
        message = "Success"
    finally:
        send_notification_mail(
            runner.definition.settings.notify,
            subject or "Logic error in main.py",
            message or "Message should not be empty.",
            mailgun_api_key,
        )
        try:
            if enable_ui and ui:
                ui.set_success(success)
                log.warning("Press q to exit")
                while not ui_greenlet.dead:
                    gevent.sleep(1)
            service_process.stop()
        except ServiceProcessException:
            service_process.kill()
        finally:
            runner.node_controller.stop()
            if ui_greenlet is not None and not ui_greenlet.dead:
                ui_greenlet.kill(ExitMainLoop)
                ui_greenlet.join()
            exit(exit_code)


@main.command(name="reclaim-eth")
@click.option(
    "--min-age",
    default=72,
    show_default=True,
    help="Minimum account non-usage age before reclaiming eth. In hours.",
)
@key_password_options
@chain_option
@data_path_option
@click.pass_context
def reclaim_eth(ctx, min_age, password, password_file, keystore_file, chain, data_path):
    from scenario_player.utils import reclaim_eth

    data_path = Path(data_path)
    if not chain:
        chain_rpc_urls = {DEFAULT_NETWORK: DEFAULT_ETH_RPC_ADDRESS}
    else:
        network, url = chain.split(":", maxsplit=1)
        chain_rpc_urls = {network: url}

    password = get_password(password, password_file)
    account = get_account(keystore_file, password)

    configure_logging_for_subcommand(construct_log_file_name("reclaim-eth", data_path))

    reclaim_eth(
        min_age_hours=min_age, chain_rpc_urls=chain_rpc_urls, data_path=data_path, account=account
    )


@main.command(name="version", help="Show versions of scenario_player and raiden environment.")
@click.option(
    "--short", is_flag=True, help="Only display scenario_player version string.", default=False
)
def version(short):
    if short:
        click.secho(message=__version__)
    else:
        spec = get_complete_spec()
        click.secho(message=json.dumps(spec, indent=2))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
