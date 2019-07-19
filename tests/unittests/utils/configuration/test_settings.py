from unittest.mock import patch

import pytest

from scenario_player.utils.configuration.base import ConfigMapping
from scenario_player.utils.configuration.settings import SettingsConfig


class TestSettingsConfig:
    def test_is_subclass_of_config_mapping(self, minimal_yaml_dict):
        """The class is a subclass of :class:`ConfigMapping`."""
        assert isinstance(SettingsConfig(minimal_yaml_dict), ConfigMapping)

    @pytest.mark.parametrize("key", ["notify", "timeout", "chain", "services", "gas_price"])
    def test_class_returns_expected_default_for_key(
        self, key, expected_defaults, minimal_yaml_dict
    ):
        """If supported  keys are absent, sensible defaults are returned for them when accessing
        them as a class attribute."""
        config = SettingsConfig(minimal_yaml_dict)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert expected_defaults["settings"][key] == actual

    def test_gas_price_strategy_returns_a_callable(self, minimal_yaml_dict):
        """The :attr:`SettingsConfig.gas_price_strategy` returns a callable."""
        config = SettingsConfig(minimal_yaml_dict)
        assert callable(config.gas_price_strategy)

    @patch("scenario_player.utils.configuration.settings.get_gas_price_strategy")
    def test_gas_price_strategy_property_calls_getter_function(
        self, mock_get_strategy, minimal_yaml_dict
    ):
        """The gas price strategy is dynamically fetched by calling
        :func:`get_gas_price_strategy` with :attr:`SettingsConfig.gas_price`."""
        config = SettingsConfig(minimal_yaml_dict)
        _ = config.gas_price_strategy
        mock_get_strategy.assert_called_once_with(config.gas_price)
