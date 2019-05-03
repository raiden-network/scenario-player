from raiden.scenario_player.services.keystore.blueprints import keystores_view
from raiden.scenario_player.services.utils import construct_flask_app


def create_keystore_service(test_config=None, secret='dev'):
    return construct_flask_app(keystores_view, db_name='keystores', test_config=test_config, secret=secret)
