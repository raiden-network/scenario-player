from raiden.scenario_player.services.releases.blueprints import releases_view, binaries_view, archives_view
from raiden.scenario_player.services.utils import construct_flask_app


def create_release_service(test_config=None, secret='dev'):
    return construct_flask_app(
        releases_view, archives_view, binaries_view, test_config=test_config, secret=secret, db_name='releases'
    )
