from typing import List, Mapping

import flask

from scenario_player.hooks import PLUGIN_BLUEPRINTS
from scenario_player.services.common.blueprints import admin_blueprint, metrics_blueprint


def attach_blueprints(app: flask.Flask, *blueprints: List[flask.Blueprint]):
    """Attach the given `blueprints` to the given `app` and return it."""
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
    return app


def construct_flask_app(
    db_name: str = "default",
    test_config: Mapping = None,
    secret: str = "dev",
    config_file: str = "config.py",
    enable_plugins: bool = True,
) -> flask.Flask:
    """Construct a flask app with the given blueprints registered.

    By default all constructed apps use the :var:`admin_blueprint` and
    :var:`metrics_blueprint`, and therefore have the following endpoints:

        `/metrics`
        Exposes prometheus compatible metrics, if available.

        `/status`
        Returns 200 OK as long as the underlying flask app is responsive and running.

        `/shutdown`
        Shuts the server down gracefully.
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

    attach_blueprints(app, metrics_blueprint, admin_blueprint)

    if enable_plugins:
        for blueprints in PLUGIN_BLUEPRINTS:
            attach_blueprints(app, *blueprints)

    return app
