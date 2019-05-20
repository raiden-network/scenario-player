import json
import logging
import os
import sys
import tarfile
import traceback
from collections import defaultdict
from datetime import datetime
from os.path import basename
from pathlib import Path

import click
import gevent
import requests
import structlog
from eth_utils import to_checksum_address
from raiden.accounts import Account
from raiden.log_config import _FIRST_PARTY_PACKAGES, configure_logging
from urwid import ExitMainLoop
from web3.utils.transactions import TRANSACTION_DEFAULTS

from scenario_player import tasks
from scenario_player.exceptions import ScenarioAssertionError, ScenarioError
from scenario_player.runner import ScenarioRunner
from scenario_player.tasks.base import collect_tasks
from scenario_player.ui import (
    LOGGING_PROCESSORS,
    NonStringifyingProcessorFormatter,
    ScenarioUI,
    UrwidLogRenderer,
    UrwidLogWalker,
)
from scenario_player.utils import (
    ChainConfigType,
    ConcatenableNone,
    DummyStream,
    send_notification_mail,
)

log = structlog.get_logger(__name__)

TRANSACTION_DEFAULTS["gas"] = lambda web3, tx: web3.eth.estimateGas(tx) * 2


@click.group(invoke_without_command=True, context_settings={"max_content_width": 120})
@click.option("--keystore-file", required=True, type=click.Path(exists=True, dir_okay=False))
@click.password_option("--password", envvar="ACCOUNT_PASSWORD", required=True)
@click.option(
    "--chain",
    "chains",
    type=ChainConfigType(),
    multiple=True,
    required=True,
    help="Chain name to eth rpc url mapping, multiple allowed",
)
@click.option(
    "--data-path",
    default=os.path.join(os.path.expanduser("~"), ".raiden", "scenario-player"),
    type=click.Path(exists=False, dir_okay=True, file_okay=False),
    show_default=True,
)
@click.option("--auth", default="")
@click.option("--mailgun-api-key")
@click.argument("scenario-file", type=click.File(), required=False)
@click.pass_context
def main(ctx, scenario_file, keystore_file, password, chains, data_path, auth, mailgun_api_key):
    gevent.get_hub().exception_stream = DummyStream()

    is_subcommand = ctx.invoked_subcommand is not None
    if not is_subcommand and scenario_file is None:
        ctx.fail("No scenario definition file provided")

    if is_subcommand:
        log_file_name = (
            f"scenario-player-{ctx.invoked_subcommand}_{datetime.now():%Y-%m-%dT%H:%M:%S}.log"
        )
    else:
        scenario_basename = basename(scenario_file.name)
        log_file_name = (
            f"{data_path}/scenarios/{scenario_basename}/{scenario_basename}_{datetime.now():%Y-%m-%dT%H:%M:%S}.log"
        )
    click.secho(f"Writing log to {log_file_name}", fg="yellow")
    configure_logging(
        {"": "INFO", "raiden": "DEBUG", "scenario_player": "DEBUG"},
        debug_log_file_name=log_file_name,
        _first_party_packages=_FIRST_PARTY_PACKAGES | frozenset(["scenario_player"]),
        _debug_log_file_additional_level_filters={"scenario_player": "DEBUG"},
    )

    log_buffer = None
    if sys.stdout.isatty() and not is_subcommand:
        log_buffer = UrwidLogWalker([])
        for handler in logging.getLogger("").handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.terminator = ConcatenableNone()
                handler.formatter = NonStringifyingProcessorFormatter(
                    UrwidLogRenderer(), foreign_pre_chain=LOGGING_PROCESSORS
                )
                handler.stream = log_buffer
                break

    chain_rpc_urls = defaultdict(list)
    for chain_name, chain_rpc_url in chains:
        chain_rpc_urls[chain_name].append(chain_rpc_url)

    with open(keystore_file, "r") as keystore:
        account = Account(json.load(keystore), password, keystore_file)
        log.info("Using account", account=to_checksum_address(account.address))

    if is_subcommand:
        ctx.obj = dict(account=account, chain_rpc_urls=chain_rpc_urls, data_path=data_path)
        return

    # Collect tasks
    collect_tasks(tasks)

    runner = ScenarioRunner(account, chain_rpc_urls, auth, Path(data_path), scenario_file)
    ui = ScenarioUI(runner, log_buffer, log_file_name)
    ui_greenlet = ui.run()
    success = False
    try:
        try:
            runner.run_scenario()
            success = True
            log.info("Run finished", result="success")
            send_notification_mail(
                runner.notification_email,
                f"Scenario successful {scenario_file.name}",
                "Success",
                mailgun_api_key,
            )
        except ScenarioAssertionError as ex:
            log.error("Run finished", result="assertion errors")
            send_notification_mail(
                runner.notification_email,
                f"Assertion mismatch in {scenario_file.name}",
                str(ex),
                mailgun_api_key,
            )
        except ScenarioError:
            log.exception("Run finished", result="scenario error")
            send_notification_mail(
                runner.notification_email,
                f"Invalid scenario {scenario_file.name}",
                traceback.format_exc(),
                mailgun_api_key,
            )
    except Exception:
        log.exception("Exception while running scenario")
        send_notification_mail(
            runner.notification_email,
            f"Error running scenario {scenario_file.name}",
            traceback.format_exc(),
            mailgun_api_key,
        )
    finally:
        try:
            if sys.stdout.isatty():
                ui.set_success(success)
                log.warning("Press q to exit")
                while not ui_greenlet.dead:
                    gevent.sleep(1)
        finally:
            if runner.is_managed:
                runner.node_controller.stop()
            if not ui_greenlet.dead:
                ui_greenlet.kill(ExitMainLoop)
                ui_greenlet.join()


@main.command(name="reclaim-eth")
@click.option(
    "--min-age",
    default=72,
    show_default=True,
    help="Minimum account non-usage age before reclaiming eth. In hours.",
)
@click.pass_obj
def reclaim_eth(obj, min_age):
    from scenario_player.utils import reclaim_eth

    reclaim_eth(min_age_hours=min_age, **obj)


@main.command('pack-logs')
@click.option(
    '--target-dir', default=os.environ.get('HOME', './'), show_default=True,
    help='Target directory to pack logs to. Defaults to your home directory.'
)
@click.option(
    '--scenario-names', 'scenario-names', required=True, multiple=True,
    help='Scenarios to pack log files for.',
)
@click.option(
    '--pack-n-latest', default=1,
    help='Specify the max num of log history you would like to pack. Defaults to 1.'
         'Specifying 0 will pack all available logs for a scenario.',
)
@click.option(
    '--raiden-dir', default=os.environ.get('HOME', '.') + '/.raiden',
    help="Path to the raiden meta data dir. Defaults to ~/.raiden.",
)
@click.option('--post-to-rocket', default=True)
def pack_logs(post_to_rocket, raiden_dir, pack_n_latest, scenario_names, target_dir):
    raiden_dir = Path(raiden_dir)
    if not raiden_dir.exists():
        raise RuntimeError(f"{raiden_dir} does not exist!")

    target_dir = Path(target_dir)
    target_dir.mkdir(exist_ok=True)

    files = set()

    for scenario_name in scenario_names:
        # The logs are located at .raiden/scenario-player/scenarios/<scenario-name> - make sure the path exists.
        scenario_log_dir = raiden_dir.joinpath('scenario-player', 'scenarios', scenario_name)
        if not scenario_log_dir.exists():
            print(f"No log directory found for scenario {scenario_name} at {scenario_log_dir}")
            continue

        # Add all folders that haven't been added yet.
        for path in scenario_log_dir.iterdir():
            if path.is_dir():
                files.add(path)

        files.union(pack_n_latest_logs_for_scenario_in_dir(scenario_name, scenario_log_dir, pack_n_latest))

    # Now that we have all our files, create a tar archive at the requested location.
    archive_fpath = target_dir.joinpath(f'Scenario_player_Logs-{"-",join(scenario_names)}-{pack_n_latest or "all"}-latest.tar.gz')
    with tarfile.open(str(archive_fpath), mode='w:gz') as archive:
        for file in files:
            archive.add(str(file))

    print(f"Created archive at {archive_fpath}")
    print(f"- {archive_fpath}")

    with tarfile.open(str(archive_fpath)) as f:
        for name in f.getnames():
            print(f"- - {name}")

    if post_to_rocket:
        post_to_rocket_chat(archive_fpath)


def pack_n_latest_logs_for_scenario_in_dir(scenario_name, scenario_log_dir: Path, n) -> set:
    # Add all scenario logs requested. Drop any iterations older than pack_n_latest,
    # or add all if that variable is 0.
    scenario_logs = [path for path in scenario_log_dir.iterdir() if (path.is_file() and str(path).startswith(scenario_name))]
    scenario_logs = sorted(scenario_logs, key=lambda x: x.stat().st_mtime, reverse=True)

    # specifying `pack_n_latest=0` will add all scenarios.
    max_range = n or len(scenario_logs)

    files = set()

    for i in range(max_range):
        try:
            files.add(scenario_logs[i])
        except IndexError:
            # We ran out of scenario logs to add before reaching the requested number of n latest logs.
            print(
                f'Only packed {i} logs of requested latest {n} '
                f'- no more logs found for {scenario_name}!',
            )
            break

    return files


def post_to_rocket_chat(fpath):
    try:
        user = os.environ['RC_USER']
        pw = os.environ['RC_PW']
        room_id = os.environ['RC_ROOM_ID']
    except KeyError:
        raise RuntimeError('Missing Rocket Char Env variables!')

    resp = requests.post(
        'https://chat.brainbot.com/api/v1/login',
        data={'username': user, 'password': pw}
    )

    token = resp.json()['data']['authToken']
    user_id = resp.json()['data']['userId']
    headers = {
        'X-Auth-Token': token,
        'X-User-Id': user_id,
    }

    with fpath.open('rb') as f:
        return requests.post(
            f'https://chat.brainbot.com/api/v1/rooms.upload/{room_id}',
            files={'file': f},
            headers=headers,
        )


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter

