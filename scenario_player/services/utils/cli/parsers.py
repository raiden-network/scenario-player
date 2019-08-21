import argparse
import pathlib

from typing import Tuple

from scenario_player.services.utils.cli.constants import SERVICE_APPS


target_service_parser = argparse.ArgumentParser()
target_service_parser.add_argument(
    "--service",
    choices=list(SERVICE_APPS.keys()),
    default="all",
    help="Specify a service to be installed. Installs entire SPaaS stack by default.",
)

raiden_dir_parser = argparse.ArgumentParser()
raiden_dir_parser.add_argument(
    "--raiden-dir",
    default=pathlib.Path.home().joinpath(".raiden"),
    help="Path to the .raiden dir. defaults to ~/.raiden",
    type=pathlib.Path,
)

netloc_parser = argparse.ArgumentParser()
netloc_parser.add_argument(
    "--port",
    default=5100,
    help="Port number to run this service on. Defaults to '5100 + n', where `n` "
         "is the number of already installed services.",
    type=int,
)
netloc_parser.add_argument(
    "--host", default="127.0.0.1", help="Host to run this service on. Defaults to '127.0.0.1'"
)


def attach_installer_cli(sub_parsers: argparse._SubParsersAction) -> Tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    remove_cmd = sub_parsers.add_parser("remove", dest="sub_command", parents=[raiden_dir_parser, target_service_parser])
    # Installing requires knowing the host and port to serve the service
    # on, hence add options to supply these.
    install_cmd = sub_parsers.add_parser("install", dest="sub_command", parents=[raiden_dir_parser, target_service_parser, netloc_parser])
    install_cmd.add_argument(
        "--port",
        default=5100,
        help="Port number to run this service on. Defaults to 5100.",
        type=int,
    )
    install_cmd.add_argument(
        "--host", default="127.0.0.1", help="Host to run this service on. Defaults to '127.0.0.1'"
    )
    return install_cmd, remove_cmd


def attach_runner_cli(sub_parsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    start_command = sub_parsers.add_parser("start",  parents=[target_service_parser, netloc_parser])
    return start_command


def construct_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub_parsers = parser.add_subparsers()
    attach_installer_cli(sub_parsers)
    attach_runner_cli(sub_parsers)
    return parser

