import logging

import structlog
import waitress

from scenario_player.services.utils.factories import (
    construct_flask_app,
    default_service_daemon_cli,
    start_daemon,
    stop_daemon,
)

log = structlog.getLogger(__name__)


def serve_spaas_stack(logfile_path, host, port):
    """Run an RPC flask app as a daemonized process."""
    logging.basicConfig(filename=logfile_path, filemode="a+", level=logging.DEBUG)
    log = structlog.getLogger()

    app = construct_flask_app()

    log.info("Starting SPaaS Service Stack", host=host, port=port)
    waitress.serve(app, host=host, port=port)


def service_daemon():
    parser = default_service_daemon_cli()

    args = parser.parse_args()

    logfile_path = args.raiden_dir.joinpath("spaas")
    logfile_path.mkdir(exist_ok=True, parents=True)
    logfile_path = logfile_path.joinpath("SPaaS-Stack.log")
    logfile_path.touch()

    PIDFILE = args.raiden_dir.joinpath("spaas", "service-stack.pid")

    if args.command == "start":
        start_daemon(
            PIDFILE,
            serve_spaas_stack,
            logfile_path,
            args.host,
            args.port,
            stdout=logfile_path,
            stderr=logfile_path,
        )
    elif args.command == "stop":
        stop_daemon(PIDFILE)
