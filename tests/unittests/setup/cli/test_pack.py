import pathlib

from scenario_player.setup.cli.pack import pack_parser
from .utils import extract_action


class TestPackOptions:

    def test_target_option_is_required(self):
        action = extract_action("target", pack_parser)
        assert action.required is True

    def test_target_option_has_expected_type(self):
        action = extract_action("target", pack_parser)
        assert action.type == pathlib.Path

    def test_run_number_has_default_value(self):
        action = extract_action("run_number", pack_parser)
        assert action.default == 1

    def test_run_number_has_expected_type(self):
        action = extract_action("run_number", pack_parser)
        assert action.type == int

    def test_run_number_option_is_optional(self):
        action = extract_action("run_number", pack_parser)
        assert action.required is False
