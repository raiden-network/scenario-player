from raiden.scenario_player.services.nodes.blueprints import nodes_view
from raiden.scenario_player.services.utils import construct_flask_app


def create_node_service(test_config=None, secret='dev'):
    return construct_flask_app(
        nodes_view, test_config=test_config, secret=secret, db_name='nodes',
    )
