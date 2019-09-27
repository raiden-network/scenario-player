import pathlib

from .utils import extract_action

from scenario_player.setup.cli.run import scenario_parser


class TestRunOptions:

    def test_scenario_option_is_required(self):
        action = extract_action("scenario", scenario_parser)
        assert action.required is True

    def test_scenario_option_converts_the_value_to_a_path(self):
        action = extract_action("scenario", scenario_parser)
        assert action.type == pathlib.Path

    def test_scenario_option_is_positional(self):
        action = extract_action("scenario", scenario_parser)
        assert action in scenario_parser._get_positional_actions()
