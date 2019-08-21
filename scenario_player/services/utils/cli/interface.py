from scenario_player.services.utils.cli.parsers import construct_parser
from scenario_player.services.utils.cli.installer import install_command
from scenario_player.services.utils.cli.runner import start_command


def main():
    parser = construct_parser()
    parsed = parser.parse_args()
    if parsed.command in ("install", "remove"):
        install_command(parsed)
    elif parsed.command == "start":
        start_command(parsed)
