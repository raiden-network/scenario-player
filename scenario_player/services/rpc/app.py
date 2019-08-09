"""Utility script to run an RPC Service instance from the command line.

TODO: Actually make use of the `--log-service` argument and configure
      logging accordingly, if given.
"""
import logging

import flask
import structlog
import waitress

from scenario_player.services.common.blueprints import admin_blueprint, metrics_blueprint
from scenario_player.services.rpc.blueprints import (
    instances_blueprint,
    tokens_blueprint,
    transactions_blueprint,
)
from scenario_player.services.rpc.utils import RPCRegistry
from scenario_player.services.utils.factories import (
    default_service_daemon_cli,
    start_daemon,
    stop_daemon,
)


def rpc_app():
    """Create a :mod:`flask` app using only the RPC blueprints."""
    from scenario_player import __version__

    log = structlog.getLogger()
    NAME = "SPaaS-RPC-Service"

    log.info("Creating RPC Flask App", version=__version__, name=NAME)

    app = flask.Flask(NAME)

    log.debug("Creating RPC Client Registry")
    app.config["rpc-client"] = RPCRegistry()

    blueprints = [
        admin_blueprint,
        instances_blueprint,
        metrics_blueprint,
        tokens_blueprint,
        transactions_blueprint,
    ]
    for bp in blueprints:
        log.debug("Registering blueprint", blueprint=bp.name)
        app.register_blueprint(bp)
    return app


def serve_rpc(logfile_path, host, port):
    """Run an RPC flask app as a daemonized process."""
    logging.basicConfig(filename=logfile_path, filemode="a+", level=logging.DEBUG)
    log = structlog.getLogger()

    app = rpc_app()

    log.info("Starting RPC Service", host=host, port=port)
    waitress.serve(app, host=host, port=port)


def service_daemon():
    parser = default_service_daemon_cli()

    args = parser.parse_args()

    logfile_path = args.raiden_dir.joinpath("spaas")
    logfile_path.mkdir(exist_ok=True, parents=True)
    logfile_path = logfile_path.joinpath("SPaaS-RPC.log")
    logfile_path.touch()

    PIDFILE = args.raiden_dir.joinpath("spaas", "rpc-service.pid")

    if args.command == "start":
        start_daemon(
            PIDFILE,
            serve_rpc,
            logfile_path,
            args.host,
            args.port,
            stdout=logfile_path,
            stderr=logfile_path,
        )
    elif args.command == "stop":
        stop_daemon(PIDFILE)
