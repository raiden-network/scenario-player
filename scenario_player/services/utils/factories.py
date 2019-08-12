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
    """Construct a flask app with the given blueprints registered.

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
