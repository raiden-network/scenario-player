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


def serve(parsed):
    from scenario_player import __version__

    logging.basicConfig(filename=".raiden/spaas/rpc.log", filemode="a+", level=logging.DEBUG)
    log = structlog.getLogger()

    NAME = "SPaaS-RPC-Service"

    log.info("Creating RPC Flask App", version=__version__, name=NAME)

    app = flask.Flask(NAME)
    print(app)
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

    waitress.serve(app, host=parsed.host, port=parsed.port)
