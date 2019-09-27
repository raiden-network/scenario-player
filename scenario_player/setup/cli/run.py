import pathlib

from scenario_player.setup.cli.base import sub_parsers
from scenario_player.setup.cli.mixins import account_options, network_options

#: CLI parser for the `scenario-player run` command.
scenario_parser = sub_parsers.add_parser("run", parents=[account_options, network_options])
scenario_parser.add_argument(
    "scenario", type=pathlib.Path, help="Path to the scenario yaml to run."
)
