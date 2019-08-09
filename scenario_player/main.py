from __future__ import annotations

import json
import os
import sys
import tarfile
import traceback
from collections import defaultdict
from datetime import datetime
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import List

import click
import gevent
import requests
import structlog
from eth_utils import to_checksum_address
from urwid import ExitMainLoop
from web3.utils.transactions import TRANSACTION_DEFAULTS

from raiden.accounts import Account
from raiden.log_config import _FIRST_PARTY_PACKAGES, configure_logging
from raiden.utils.cli import EnumChoiceType
from scenario_player import tasks
from scenario_player.exceptions import ScenarioAssertionError, ScenarioError
from scenario_player.exceptions.services import ServiceProcessException
from scenario_player.runner import ScenarioRunner
from scenario_player.services.common.app import ServiceProcess
from scenario_player.tasks.base import collect_tasks
from scenario_player.ui import ScenarioUI, attach_urwid_logbuffer
from scenario_player.utils import (
    ChainConfigType,
    DummyStream,
    post_task_state_to_rc,
    send_notification_mail,
)

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


def parse_chain_rpc_urls(list_of_urls):
    chain_rpc_urls = defaultdict(list)
    for chain_name, chain_rpc_url in list_of_urls:
        chain_rpc_urls[chain_name].append(chain_rpc_url)
    return chain_rpc_urls


def load_account_obj(keystore_file, password):
    with open(keystore_file, "r") as keystore:
        account = Account(json.load(keystore), password, keystore_file)
        log.info("Using account", account=to_checksum_address(account.address))
        return account


@click.group(invoke_without_command=True, context_settings={"max_content_width": 120})
@click.option(
    "--data-path",
    default=str(Path.home().joinpath(".raiden", "scenario-player")),
    type=click.Path(exists=False, dir_okay=True, file_okay=False),
    show_default=True,
)
@click.option(
    "--chain",
    "chains",
    type=ChainConfigType(),
    multiple=True,
    required=True,
    help="Chain name to eth rpc url mapping, multiple allowed",
)
@click.pass_context
def main(ctx, chains, data_path):
    gevent.get_hub().exception_stream = DummyStream()
    chain_rpc_urls = parse_chain_rpc_urls(chains)

    if ctx.invoked_subcommand:
        ctx.obj = dict(chain_rpc_urls=chain_rpc_urls, data_path=Path(data_path))


@main.command(name="run")
@click.argument("scenario-file", type=click.File(), required=False)
@click.option("--keystore-file", required=True, type=click.Path(exists=True, dir_okay=False))
@click.password_option("--password", envvar="ACCOUNT_PASSWORD", required=True)
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
@click.pass_context
def run(
    ctx, mailgun_api_key, auth, password, keystore_file, scenario_file, notify_tasks, enable_ui
):
    scenario_file = Path(scenario_file.name).absolute()
    data_path = ctx.obj["data_path"]
    chain_rpc_urls = ctx.obj["chain_rpc_urls"]

    log_file_name = construct_log_file_name("run", data_path, scenario_file)
    configure_logging_for_subcommand(log_file_name)

    account = load_account_obj(keystore_file, password)

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
    runner = ScenarioRunner(
        account, chain_rpc_urls, auth, data_path, scenario_file, notify_tasks_callable
    )
    ui = None
    ui_greenlet = None
    if enable_ui:
        ui = ScenarioUI(runner, log_buffer, log_file_name)
        ui_greenlet = ui.run()
    success = False

    try:
        try:
            runner.run_scenario()
        except ScenarioAssertionError as ex:
            log.error("Run finished", result="assertion errors")
            send_notification_mail(
                runner.yaml.settings.notify,
                f"Assertion mismatch in {scenario_file.name}",
                str(ex),
                mailgun_api_key,
            )
        except ScenarioError:
            log.exception("Run finished", result="scenario error")
            send_notification_mail(
                runner.yaml.settings.notify,
                f"Invalid scenario {scenario_file.name}",
                traceback.format_exc(),
                mailgun_api_key,
            )
        else:
            success = True
            log.info("Run finished", result="success")
            send_notification_mail(
                runner.yaml.settings.notify,
                f"Scenario successful {scenario_file.name}",
                "Success",
                mailgun_api_key,
            )
    except Exception:
        log.exception("Exception while running scenario")
        send_notification_mail(
            runner.yaml.settings.notify,
            f"Error running scenario {scenario_file.name}",
            traceback.format_exc(),
            mailgun_api_key,
        )
    finally:
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


@main.command(name="reclaim-eth")
@click.option("--keystore-file", required=True, type=click.Path(exists=True, dir_okay=False))
@click.password_option("--password", envvar="ACCOUNT_PASSWORD", required=True)
@click.option(
    "--min-age",
    default=72,
    show_default=True,
    help="Minimum account non-usage age before reclaiming eth. In hours.",
)
@click.pass_context
def reclaim_eth(ctx, min_age, password, keystore_file):
    from scenario_player.utils import reclaim_eth

    data_path = ctx.obj["data_path"]
    chain_rpc_urls = ctx.obj["chain_rpc_urls"]
    account = load_account_obj(keystore_file, password)

    configure_logging_for_subcommand(construct_log_file_name("reclaim-eth", data_path))

    reclaim_eth(
        min_age_hours=min_age, chain_rpc_urls=chain_rpc_urls, data_path=data_path, account=account
    )


@main.command("pack-logs")
@click.option(
    "--target-dir",
    default=os.environ.get("HOME", "./"),
    show_default=True,
    help="Target directory to pack logs to. Defaults to your home directory.",
)
@click.option(
    "--pack-n-latest",
    default=1,
    help="Specify the max num of log history you would like to pack. Defaults to 1."
    "Specifying 0 will pack all available logs for a scenario.",
)
@click.option("--post-to-rocket/--no-post-to-rocket", default=True)
@click.argument("scenario-file", type=click.File(), required=True)
@click.pass_context
def pack_logs(ctx, scenario_file, post_to_rocket, pack_n_latest, target_dir):
    data_path: Path = ctx.obj["data_path"].absolute()
    scenario_file = Path(scenario_file.name).absolute()
    scenario_name = Path(scenario_file.name).stem
    log_file_name = construct_log_file_name("pack-logs", data_path, scenario_file)
    configure_logging_for_subcommand(log_file_name)

    target_dir = Path(target_dir)
    target_dir.mkdir(exist_ok=True)

    # The logs are located at .raiden/scenario-player/scenarios/<scenario-name>
    # - make sure the path exists.
    scenarios_path = data_path.joinpath("scenarios")
    scenario_log_dir = scenarios_path.joinpath(scenario_name)
    if not scenario_log_dir.exists():
        print(f"No log directory found for scenario {scenario_name} at {scenario_log_dir}")
        return

    # List all folders
    folders = [path for path in scenario_log_dir.iterdir() if path.is_dir()]

    # List all files that match the filters `scenario_name` and the `pack_n_latest` counter.
    files = pack_n_latest_logs_for_scenario_in_dir(scenario_name, scenario_log_dir, pack_n_latest)

    # Now that we have all our files, create a tar archive at the requested location.
    archive_fpath = target_dir.joinpath(
        f'Scenario_player_Logs-{scenario_name}-{pack_n_latest or "all"}-latest'
        f"-{datetime.today():%Y-%m-%d}.tar.gz"
    )

    with tarfile.open(str(archive_fpath), mode="w:gz") as archive:
        for obj in chain(folders, files):
            archive.add(str(obj), arcname=str(obj.relative_to(scenarios_path)))

    # Print some feedback to stdout. This is also a sanity check,
    # asserting the archive is readable.
    # Race conditions are ignored.
    print(f"Created archive at {archive_fpath}")
    print(f"- {archive_fpath}")
    with tarfile.open(str(archive_fpath)) as f:
        for name in f.getnames():
            print(f"- - {name}")

    if post_to_rocket:
        rc_message = {"msg": None, "description": None}
        if pack_n_latest == 1:
            # Index 0 will always return the latest log file for the scenario.
            rc_message["text"] = construct_rc_message(target_dir, archive_fpath, files[0])
            rc_message["description"] = f"Log files for scenario {scenario_name}"
        post_to_rocket_chat(archive_fpath, **rc_message)


def pack_n_latest_logs_for_scenario_in_dir(scenario_name, scenario_log_dir: Path, n) -> List[Path]:
    """ Add the `n` latest log files for ``scenario_name`` in ``scenario_dir`` to a :cls:``set``
        and return it.
    """
    scenario_logs = [
        path for path in scenario_log_dir.iterdir() if (path.is_file() and "-run_" in path.name)
    ]
    history = sorted(scenario_logs, key=lambda x: x.stat().st_mtime, reverse=True)

    # Can't pack more than the number of available logs.
    num_of_packable_iterations = n or len(scenario_logs)

    if not history:
        raise RuntimeError(f"No Scenario logs found in {scenario_log_dir}")

    if num_of_packable_iterations < n:
        # We ran out of scenario logs to add before reaching the requested number of n latest logs.
        print(
            f"Only packing {num_of_packable_iterations} logs of requested latest {n} "
            f"- no more logs found for {scenario_name}!"
        )

    return history[:num_of_packable_iterations]


def construct_rc_message(base_dir, packed_log, log_fpath) -> str:
    """Check the result of the log file at the given `log_fpath`."""
    result = None
    exc = None
    with log_fpath.open("r") as f:
        for line in f:
            json_obj = json.loads(line.strip())
            if "result" in json_obj:
                result = json_obj["result"]
                exc = json_obj.get("exception", None)
    if result == "success":
        return ":white_check_mark: Succesfully ran scenario!"
    elif result is None:
        message = f":skull_and_crossbones: Scenario incomplete. No result found in log file."
    else:
        message = f":x: Error while running scenario: {result}!"
        if exc:
            message += "\n```\n" + exc + "\n```"
    message += (
        f"\nLog can be downloaded from:\n"
        f"http://scenario-player.ci.raiden.network/{packed_log.relative_to(base_dir)}"
    )
    return message


def post_to_rocket_chat(fpath, **rc_payload_fields):
    try:
        user = os.environ["RC_USER"]
        pw = os.environ["RC_PW"]
        room_id = os.environ["RC_ROOM_ID"]
        room_name = "#" + os.environ["RC_ROOM_NAME"]

    except KeyError as e:
        raise RuntimeError("Missing Rocket Char Env variables!") from e

    resp = requests.post(
        "https://chat.brainbot.com/api/v1/login", data={"username": user, "password": pw}
    )

    rc_payload_fields["room_id"] = room_id
    rc_payload_fields["channel"] = room_name
    token = resp.json()["data"]["authToken"]
    user_id = resp.json()["data"]["userId"]
    headers = {"X-Auth-Token": token, "X-User-Id": user_id}

    resp = requests.post(
        f"https://chat.brainbot.com/api/v1/chat.postMessage",
        headers=headers,
        data=rc_payload_fields,
    )
    resp.raise_for_status()


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
