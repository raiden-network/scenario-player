import pytest

from scenario_player.utils.configuration.nodes import NodesConfig


class TestNodesConfig:
    @pytest.mark.parametrize(
        "key", ["default_options", "node_options", "raiden_version", "commands"]
    )
    def test_class_returns_expected_default_for_key(
        self, key, expected_defaults, minimal_definition_dict
    ):
        """If supported  keys are absent, sensible defaults are returned for them when accessing
        them as a class attribute."""
        config = NodesConfig(minimal_definition_dict)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert expected_defaults["nodes"][key] == actual

    @pytest.mark.parametrize("key", ["count"])
    def test_class_returns_required_keys(self, key, minimal_definition_dict):
        """Required keys are accessible via identically named class attributes."""
        config = NodesConfig(minimal_definition_dict)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert minimal_definition_dict["nodes"][key] == actual

    @pytest.mark.parametrize("key", ["count"])
    def test_missing_required_key_raises_node_configuration_error(
        self, key, minimal_definition_dict
    ):
        """OMissing required keys in the config dict raises an Exception."""
        minimal_definition_dict["nodes"].pop(key)
        with pytest.raises(Exception):
            NodesConfig(minimal_definition_dict)

    def test_instantiating_with_an_empty_dict_raises_node_configuration_error(self):
        """Passing the NodeConfig class an empty dict is not allowed."""
        with pytest.raises(Exception):
            NodesConfig({})
