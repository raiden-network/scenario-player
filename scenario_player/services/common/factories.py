import flask

from scenario_player.services.common.blueprints import metrics_view


def construct_flask_app(
    *blueprints, db_name="default", test_config=None, secret="dev", config_file="config.py"
):
    """Construct a flask app with the given blueprints registered.

    By default all constructed apps have `/metrics` endpoint, which exposes
    prometheus compatible metrics, if available.
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

    app.register_blueprint(metrics_view)
    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    return app
