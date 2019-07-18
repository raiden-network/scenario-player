import pytest

from scenario_player.exceptions.config import NodeConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping
from scenario_player.utils.configuration.nodes import NodesConfig


class TestNodesConfig:
    def test_is_subclass_of_config_mapping(self, minimal_yaml_dict):
        assert isinstance(NodesConfig(minimal_yaml_dict), ConfigMapping)

    @pytest.mark.parametrize(
        "key", ["default_options", "node_options", "raiden_version", "commands"]
    )
    def test_class_returns_expected_default_for_key(
        self, key, expected_defaults, minimal_yaml_dict
    ):
        config = NodesConfig(minimal_yaml_dict)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert expected_defaults["nodes"][key] == actual

    @pytest.mark.parametrize("key", ["count", "list"])
    def test_class_returns_required_keys(self, key, minimal_yaml_dict):
        config = NodesConfig(minimal_yaml_dict)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert minimal_yaml_dict["nodes"][key] == actual

    @pytest.mark.parametrize("key", ["list", "count"])
    def test_missing_required_key_raises_node_configuration_error(self, key, minimal_yaml_dict):
        minimal_yaml_dict.pop(key)
        with pytest.raises(NodeConfigurationError):
            NodesConfig(minimal_yaml_dict)

    def test_instantiating_with_an_empty_dict_raises_node_configuration_error(self):
        with pytest.raises(NodeConfigurationError):
            NodesConfig({})
