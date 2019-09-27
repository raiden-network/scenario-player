import argparse
import pathlib

#: Basic required/optional CLI flags supported across all commands.
root_parser = argparse.ArgumentParser()
root_parser.add_argument(
    "--notify", nargs=1, default=None, choices=["rc", "mail", "all"]
)
root_parser.add_argument(
    "--data-dir", default=pathlib.Path.home().joinpath(".raiden"), nargs=1
)
root_parser.add_argument(
    "--disable-gui",
    default=False,
    help="Disable fancy terminal output.",
    action="store_true",
)

#: Sub-command parsers for `run`, `reclaim`, and `pack`
sub_parsers = root_parser.add_subparsers()
