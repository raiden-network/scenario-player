import pathlib

from scenario_player.setup.cli.base import sub_parsers
from scenario_player.setup.cli.mixins import account_options, network_options

#: CLI parser for the `scenario-player reclaim-eth` command.
reclaim_parser = sub_parsers.add_parser("reclaim", parents=[account_options, network_options])
reclaim_parser.add_argument(
    "scenario", type=pathlib.Path, help="Path to the scenario yaml to reclaim funds for."
)
reclaim_parser.add_argument(
    "--min-age",
    default=24,
    type=int,
    help="Time since the last run in hours of the given scenario before we can reclaim its funds.",
)
