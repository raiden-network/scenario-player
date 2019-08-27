import argparse
import pathlib
from typing import Mapping

import flask

from scenario_player.hooks import SP_PM


def construct_flask_app(
    db_name: str = "default",
    test_config: Mapping = None,
    secret: str = "dev",
    config_file: str = "config.py",
    enable_plugins: bool = True,
) -> flask.Flask:
    """Construct a flask app with a set of default blueprints registered.

    By default all constructed apps use the :var:`admin_blueprint` and
    :var:`metrics_blueprint`, and therefore have the following endpoints:

        `/metrics`
        Exposes prometheus compatible metrics, if available.

        `/status`
        Returns 200 OK as long as the underlying flask app is responsive and running.

        `/shutdown`
        Shuts the server down gracefully.

    Additionally, any blueprints supplied by plugins are also automatically injected,
    unless `enable_plugins` is `False`.
    """
    # create and configure the app
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY=secret, DATABASE=db_name)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile(config_file, silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    if enable_plugins:
        # Register blueprints supplied by plugins.
        SP_PM.hook.register_blueprints(app=app)

    return app


def default_service_daemon_cli():
    """Create an :class:`argparse.ArgumentParser` with a minimalistic set of CLI options.

    Configures the following options:

        * <command> (required) - must be one of `start` or `stop`.
        * --port (optional) - the port to assign to the service. Defaults to 5100.
        * --host (optional) - the host to assign to the service. Defaults to 127.0.0.1
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["start", "stop"])
    parser.add_argument(
        "--port",
        default=5100,
        help="Port number to run this service on. Defaults to '5100'",
        type=int,
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to run this service on. Defaults to '127.0.0.1'"
    )
    parser.add_argument("--log-service", default=None, help="netloc of a SPaaS Logging Service.")
    parser.add_argument(
        "--raiden-dir",
        default=pathlib.Path.home().joinpath(".raiden"),
        help="Path to the .raiden dir. defaults to ~/.raiden",
        type=pathlib.Path,
    )
    return parser
