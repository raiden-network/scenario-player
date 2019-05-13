from scenario_player.services.scenario.blueprints import scenario_view, runner_view, validate_view
from scenario_player.services.common.factories import construct_flask_app


def create_scenario_service(test_config=None, secret='dev'):
    return construct_flask_app(
        runner_view, scenario_view, validate_view, test_config=test_config, secret=secret, db_name='scenarios',
    )
