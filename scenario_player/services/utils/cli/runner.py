from scenario_player.services.utils.cli.constants import SERVICE_APPS


def start_command(parsed):
    serve_func = SERVICE_APPS[parsed.service]
    serve_func(parsed)
