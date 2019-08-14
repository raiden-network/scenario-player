import logging

import structlog
import waitress
from daemonize import Daemonize

from scenario_player.services.utils.factories import (
    construct_flask_app,
    default_service_daemon_cli,
)

log = structlog.getLogger(__name__)


def service_daemon():
    parser = default_service_daemon_cli()

    args = parser.parse_args()

    logfile_path = args.raiden_dir.joinpath("spaas")
    logfile_path.mkdir(exist_ok=True, parents=True)
    logfile_path = logfile_path.joinpath("SPaaS-Stack.log")
    logfile_path.touch()

    PIDFILE = args.raiden_dir.joinpath("spaas", "service-stack.pid")

    host, port = args.host, args.port

    def serve_spaas_stack():
        """Run an RPC flask app as a daemonized process."""
        logging.basicConfig(filename=logfile_path, filemode="a+", level=logging.DEBUG)
        log = structlog.getLogger()

        app = construct_flask_app()

        log.info("Starting SPaaS Service Stack", host=host, port=port)
        waitress.serve(app, host=host, port=port)

    daemon = Daemonize("SPaaS-RPC", PIDFILE, serve_spaas_stack)

    if args.command == "start":
        daemon.start()
    elif args.command == "stop":
        daemon.exit()
