from raiden.scenario_player.services.common.blueprints import metrics_view
from raiden.scenario_player.services.common.factories import construct_flask_app
from raiden.scenario_player.services.keystore.blueprints import keystores_view
from raiden.scenario_player.services.nodes.blueprints import nodes_view
from raiden.scenario_player.services.scenario.blueprint import runner_view, scenario_view
from raiden.scenario_player.services.releases.blueprints import binaries_views, archives_views, releases_views


def create_master_service(test_config=None, secret='dev', db_name='default'):
    """Create a flask app containing all services available at :lib:`raiden.scenario_player.services`."""
    blueprints = [
        metrics_view,
        keystores_view,
        nodes_view,
        runner_view,
        scenario_view,
        binaries_views,
        archives_views,
        releases_views,
    ]
    return construct_flask_app(*blueprints, test_config=test_config, secret=secret, db_name=db_name)
