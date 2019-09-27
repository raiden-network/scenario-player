from unittest.mock import patch

import pathlib
from .utils import extract_action

from scenario_player.setup.cli.mixins import account_options, network_options


class TestAccountOptions:

    def test_keystore_option_is_required(self):
        action = extract_action("keystore", account_options)
        assert action.required is True

    def test_keystore_option_takes_one_argument_and_converts_the_value_to_a_path(self):
        action = extract_action("keystore", account_options)
        assert action.nargs == 1
        assert action.type == pathlib.Path

    def test_keystore_pw_is_required(self):
        action = extract_action("keystore_pw", account_options)
        assert action.required is True

    def test_keystore_pw_option_takes_one_argument_and_converts_the_value_to_a_path(self):
        action = extract_action("keystore_pw", account_options)
        assert action.type == pathlib.Path
        assert action.nargs == 1


class TestNetworkOptions:

    def test_network_option_is_required(self):
        action = extract_action("network", network_options)
        assert action.required is True

    def test_rpc_address_is_required(self):
        action = extract_action("rpc_address", network_options)
        assert action.required is True
