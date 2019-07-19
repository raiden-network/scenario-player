import json
from unittest.mock import patch

import pytest

from scenario_player.constants import DEFAULT_TOKEN_BALANCE_FUND, DEFAULT_TOKEN_BALANCE_MIN
from scenario_player.exceptions.config import TokenConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping
from scenario_player.utils.configuration.token import TokenConfig


class TestTokenConfig:
    def test_is_subclass_of_config_mapping(self, minimal_yaml_dict, token_info_path):
        """The class is a subclass of :class:`ConfigMapping`."""
        assert isinstance(TokenConfig(minimal_yaml_dict, token_info_path), ConfigMapping)

    @pytest.mark.parametrize("key", ["address", "decimals"])
    def test_class_returns_expected_default_for_key(
        self, key, expected_defaults, minimal_yaml_dict, token_info_path
    ):
        """If supported  keys are absent, sensible defaults are returned for them when accessing
        them as a class attribute."""
        config = TokenConfig(minimal_yaml_dict, token_info_path)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert expected_defaults["token"][key] == actual

    def test_passing_mutual_exclusive_keys_raises_configuration_error(
        self, minimal_yaml_dict, token_info_path
    ):
        minimal_yaml_dict["token"]["reuse"] = True
        minimal_yaml_dict["token"]["address"] = "some_address"
        with pytest.raises(TokenConfigurationError):
            TokenConfig(minimal_yaml_dict, token_info_path)

    @pytest.mark.parametrize("exists", [True, False])
    @pytest.mark.parametrize("reuse", [True, False])
    def test_reuse_token_property_returns_correct_boolean(
        self, reuse, exists, minimal_yaml_dict, token_info_path
    ):
        """The :attr:`TokenConfig.reuse_token` returns a boolean depending on
        the `reuse` key value and the existence of a `token.info` file in the data path."""
        if not exists:
            token_info_path.unlink()
        minimal_yaml_dict["token"]["reuse"] = reuse

        config = TokenConfig(minimal_yaml_dict, token_info_path)

        assert config.reuse_token == (reuse and exists)

    @pytest.mark.parametrize("reuse", [True, False])
    def test_save_token_property_returns_boolean_according_to_reuse_key(
        self, reuse, minimal_yaml_dict, token_info_path
    ):
        """The :attr:`TokenConfig.save_token` attribute's value is identical
        to the `reuse` key value."""
        minimal_yaml_dict["token"]["reuse"] = reuse
        config = TokenConfig(minimal_yaml_dict, token_info_path)
        assert config.save_token == reuse

    def test_symbol_property_uses_token_id_to_generate_symbol_if_not_given_in_config(
        self, minimal_yaml_dict, token_info_path
    ):
        """We generate a symbol if none is given, using the token id."""
        config = TokenConfig(minimal_yaml_dict, token_info_path)
        assert config.symbol == f"T{config._token_id!s:.3}"

    @patch("scenario_player.utils.configuration.token.uuid.uuid4", return_value="turtles")
    def test_token_id_is_generated_using_uuid4(
        self, mock_uuuid4, minimal_yaml_dict, token_info_path
    ):
        """The token_id is generated using :func:`uuid.uuid4()`."""
        config = TokenConfig(minimal_yaml_dict, token_info_path)
        mock_uuuid4.assert_called_once()
        assert config._token_id == "turtles"

    def test_name_property_loads_token_name_from_token_info_path_file_if_reuse_token_is_true(
        self, minimal_yaml_dict, token_info_path
    ):
        """Load token name from token info, if available."""
        minimal_yaml_dict["token"]["reuse"] = True
        assert token_info_path.exists()
        assert json.loads(token_info_path.read_text())
        config = TokenConfig(minimal_yaml_dict, token_info_path)
        assert config.name == "my_token"

    def test_balancing_keys_are_accessible_via_attributes(
        self, minimal_yaml_dict, token_info_path
    ):
        """The keys 'balance_min' and `balance_fund` are accessible via attributes.

        The accessor attributes are:

            * min_balance -> balance_min key
            * max_funding -> balance_fund key
        """
        minimal_yaml_dict["token"]["balance_min"] = 66
        minimal_yaml_dict["token"]["balance_fund"] = 99

        config = TokenConfig(minimal_yaml_dict, token_info_path)
        assert config.min_balace == 66
        assert config.max_funding == 99

    def test_balancing_attrs_return_defaults_if_keys_are_absent(
        self, minimal_yaml_dict, token_info_path
    ):
        """The attributes 'min_balance' and `max_funding` return defaults if their keys are absent."""

        config = TokenConfig(minimal_yaml_dict, token_info_path)
        assert config.min_balace == DEFAULT_TOKEN_BALANCE_MIN
        assert config.max_funding == DEFAULT_TOKEN_BALANCE_FUND
