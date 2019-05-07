from raiden.scenario_player.services.common.factories import construct_flask_app
from raiden.scenario_player.services.keystore.blueprints import keystores_view
from raiden.scenario_player.services.nodes.blueprints import nodes_view
from raiden.scenario_player.services.scenario.blueprints import scenario_view
from raiden.scenario_player.services.releases.blueprints import binaries_views, archives_views, releases_views
from raiden.scenario_player.services.runner.blueprints import runner_view


def create_master_service(test_config=None, secret='dev', db_name='default'):
    """Create a flask app containing all services available at :lib:`raiden.scenario_player.services`."""
    blueprints = [
        keystores_view,
        nodes_view,
        runner_view,
        scenario_view,
        binaries_views,
        archives_views,
        releases_views,
    ]
    return construct_flask_app(*blueprints, test_config=test_config, secret=secret, db_name=db_name)
