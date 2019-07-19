from collections import Mapping

import pytest

from scenario_player.utils.configuration.base import ConfigMapping, ConfigurationError


class TestConfigMapping:
    def test_class_is_a_mapping(self):
        assert isinstance(ConfigMapping({}), Mapping)

    def test_assert_option_raises_exception_if_expression_is_false(self):
        with pytest.raises(ConfigurationError):
            ConfigMapping.assert_option(True is False)

    def test_assert_option_completes_silently_if_expression_is_true(self):
        ConfigMapping.assert_option(True is True)

    def test_assert_option_raises_configuration_error_with_given_message(self):
        expected_message = "Custom message"
        with pytest.raises(ConfigurationError, match=expected_message):
            ConfigMapping.assert_option(True is False, expected_message)

    def test_assert_option_raises_custom_exception_if_exception_is_passed(self):
        with pytest.raises(SyntaxError):
            ConfigMapping.assert_option(True is False, SyntaxError)
