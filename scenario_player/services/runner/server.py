from scenario_player.services.runner.blueprints import runner_view
from scenario_player.services.common.factories import construct_flask_app


def create_runner_service(test_config=None, secret='dev'):
    return construct_flask_app(
        runner_view, test_config=test_config, secret=secret, db_name='runner',
    )
