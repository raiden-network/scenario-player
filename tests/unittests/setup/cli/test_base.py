from scenario_player.setup.cli.base import root_parser
import pathlib

from .utils import extract_action


class TestRootParser:
    def test_notify_defaults_to_none_value(self):
        action = extract_action("notify", root_parser)
        assert action.default is None

    def test_notify_limits_allowed_choices(self):
        allowed = ["rc", "mail", "all"]
        action = extract_action("notify", root_parser)
        assert action.choices == allowed, "Unexpected allowed choices for flag!"

    def test_disable_gui_converts_to_bool(self):
        action = extract_action("disable_gui", root_parser)
        assert action.default is False, "Does not set False if absent"
        assert action.const is True, "Does not set True if given"

    def test_data_dir_flag_defaults_to_default_raiden_dir(self):
        action = extract_action("data_dir", root_parser)
        assert action.default == pathlib.Path.home().joinpath(".raiden")

    def test_data_dir_is_not_required(self):
        action = extract_action("data_dir", root_parser)
        assert action.required is False
