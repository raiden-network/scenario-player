import pathlib

from .utils import extract_action

from scenario_player.setup.cli.reclaim import reclaim_parser


class TestReclaimOptions:

    def test_scenario_option_is_required(self):
        action = extract_action("scenario", reclaim_parser)
        assert action.required is True

    def test_scenario_option_converts_the_value_to_a_path(self):
        action = extract_action("scenario", reclaim_parser)
        assert action.type == pathlib.Path

    def test_scenario_option_is_positional(self):
        action = extract_action("scenario", reclaim_parser)
        assert action in reclaim_parser._get_positional_actions()

    def test_min_age_option_is_not_required_and_has_default(self):
        action = extract_action("min_age", reclaim_parser)
        assert action.required is False
        assert action.default == 24

    def test_min_age_converts_to_int_type(self):
        action = extract_action("min_age", reclaim_parser)
        assert action.type == int
