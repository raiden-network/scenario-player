from scenario_player.services.releases.blueprints import archives_views, binaries_views, releases_views
from scenario_player.services.common.factories import construct_flask_app


def create_release_service(test_config=None, secret='dev'):
    return construct_flask_app(
        archives_views, binaries_views, releases_views, test_config=test_config, secret=secret, db_name='releases'
    )
