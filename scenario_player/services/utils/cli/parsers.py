import argparse
import pathlib
from typing import Tuple

from scenario_player.services.utils.cli.constants import SERVICE_APPS

target_service_parser = argparse.ArgumentParser(add_help=False)
target_service_parser.add_argument(
    "--service",
    choices=list(SERVICE_APPS.keys()),
    default="all",
    type=str.upper,
    help="Specify service to target. Selects entire SPaaS stack by default.",
)

raiden_dir_parser = argparse.ArgumentParser(add_help=False)
raiden_dir_parser.add_argument(
    "--raiden-dir",
    default=pathlib.Path.home().joinpath(".raiden"),
    help="Path to the .raiden dir. Defaults to ~/.raiden",
    type=pathlib.Path,
)

netloc_parser = argparse.ArgumentParser(add_help=False)
netloc_parser.add_argument("--port", default=5100, help="Service port. Defaults to 5100", type=int)
netloc_parser.add_argument(
    "--host", default="127.0.0.1", help="Service host. Defaults to '127.0.0.1'"
)


def attach_installer_cli(
    sub_parsers: argparse._SubParsersAction
) -> Tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    remove_cmd = sub_parsers.add_parser(
        "remove", parents=[raiden_dir_parser, target_service_parser]
    )
    install_cmd = sub_parsers.add_parser(
        "install", parents=[raiden_dir_parser, target_service_parser, netloc_parser]
    )
    return install_cmd, remove_cmd


def attach_runner_cli(sub_parsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    start_command = sub_parsers.add_parser("start", parents=[target_service_parser, netloc_parser])
    return start_command


def construct_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub_parsers = parser.add_subparsers(dest="command")
    attach_installer_cli(sub_parsers)
    attach_runner_cli(sub_parsers)
    return parser
