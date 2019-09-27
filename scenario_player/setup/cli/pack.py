import pathlib

from scenario_player.setup.cli.base import sub_parsers

#: CLI parser for the `scenario-player pack-logs` command.
pack_parser = sub_parsers.add_parser("pack")
pack_parser.add_argument(
    "--target",
    type=pathlib.Path,
    help="Path at which the resulting archive should be created at.",
    required=True,
)
pack_parser.add_argument(
    "--run-number",
    default=1,
    type=int,
    help="The number of runs to pack logs for; stating 1 will pack the latest, "
         "2 the 2 latest runs, and giving 0 will pack all of them.",
)
