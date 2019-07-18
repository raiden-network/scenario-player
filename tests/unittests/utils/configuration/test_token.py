from unittest.mock import patch

import pytest

from scenario_player.exceptions.config import NodeConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping
from scenario_player.utils.configuration.token import TokenConfig


class TestTokenConfig:
    def test_is_subclass_of_config_mapping(self, minimal_yaml_dict):
        assert isinstance(TokenConfig(minimal_yaml_dict), ConfigMapping)

    @pytest.mark.parametrize("key", ["address", "block", "decimals"])
    def test_class_returns_expected_default_for_key(
        self, key, expected_defaults, minimal_yaml_dict, tmp_path
    ):
        config = TokenConfig(minimal_yaml_dict, tmp_path)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert expected_defaults["nodes"][key] == actual

    def test_passing_mutual_exclusive_keys_raises_configuration_error(
        self, minimal_yaml_dict, tmp_path
    ):
        minimal_yaml_dict["token"]["reuse"] = True
        minimal_yaml_dict["token"]["address"] = "some_address"
        with pytest.raises(NodeConfigurationError):
            TokenConfig(minimal_yaml_dict, tmp_path)

    def test_instantiating_with_an_empty_dict_raises_node_configuration_error(self, tmp_path):
        with pytest.raises(NodeConfigurationError):
            TokenConfig({}, tmp_path)

    @pytest.mark.parametrize("exists", [(True, False)])
    @pytest.mark.parametrize("reuse", [(True, False)])
    def test_reuse_token_property_returns_correct_boolean(
        self, reuse, exists, minimal_yaml_dict, tmp_path
    ):
        if exists:
            tmp_path.joinpath("token.info").touch()
        minimal_yaml_dict["token"]["reuse"] = reuse

        config = TokenConfig(minimal_yaml_dict, tmp_path)

        assert config.reuse_token == (reuse and exists)

    @pytest.mark.parametrize("reuse", [True, False])
    def test_save_token_property_returns_boolean_according_to_reuse_key(
        self, reuse, minimal_yaml_dict, tmp_path
    ):
        minimal_yaml_dict["token"]["reuse"] = reuse
        config = TokenConfig(minimal_yaml_dict, tmp_path)
        assert config.save_token == reuse

    def test_symbol_property_uses_token_id_to_generate_symbol_if_not_given_in_config(
        self, minimal_yaml_dict, tmp_path
    ):
        config = TokenConfig(minimal_yaml_dict, tmp_path)
        assert config.symbol == f"T{config._token_id!s:.3}"

    @patch("scenario_player.utils.configuration.token.uuid.uuid4", return_value="turtles")
    def test_token_id_is_generated_using_uuid4(self, mock_uuuid4, minimal_yaml_dict, tmp_path):
        config = TokenConfig(minimal_yaml_dict, tmp_path)
        mock_uuuid4.assert_called_once()
        assert config._token_id == "turtles"
