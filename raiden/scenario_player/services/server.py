import pathlib

from flask import Flask

from raiden.scenario_player.services.scenario.blueprint import runner_view, scenario_view
from raiden.scenario_player.services.releases.blueprints import binaries_views, archives_views, releases_views
from raiden.scenario_player.services.nodes.blueprints import nodes_view
from raiden.scenario_player.services.keystore.blueprints import keystores_view


def create_master_service(test_config=None, secret='dev'):
    """Create a flask app containing all services available at :lib:`raiden.scenario_player.services`."""
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=secret,
        DATABASE=pathlib.Path(app.instance_path).joinpath('scenario-player.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    app.register_blueprint(scenario_view)
    app.register_blueprint(runner_view)
    app.register_blueprint(binaries_views)
    app.register_blueprint(archives_views)
    app.register_blueprint(releases_views)
    app.register_blueprint(nodes_view)
    app.register_blueprint(keystores_view)

    # ensure the instance folder exists
    pathlib.Path.mkdir(app.instance_path, parents=True, exist_ok=True)

    return app
