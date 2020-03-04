from collections import Mapping

import pytest

from scenario_player.utils.configuration.base import ConfigMapping, ConfigurationError


class TestConfigMapping:
    def test_class_is_a_mapping(self):
        """The class is a subclass of :class:`collections.abc.Mapping`."""
        assert isinstance(ConfigMapping({}), Mapping)

    def test_assert_option_raises_exception_if_expression_is_false(self):
        """:meth:`ConfigMapping.assert_option` raises an exception if expession is False."""

    with pytest.raises(ConfigurationError):
        ConfigMapping.assert_option(False)

    def test_assert_option_completes_silently_if_expression_is_true(self):
        """:meth:`ConfigMapping.assert_option` raises no exception if expession is True."""

    ConfigMapping.assert_option(True)

    def test_assert_option_raises_configuration_error_with_given_message(self):
        """:meth:`ConfigMapping.assert_option` allows raise :exc:`ConfigurationError`
        with given message."""
        expected_message = "Custom message"
        with pytest.raises(ConfigurationError, match=expected_message):
            ConfigMapping.assert_option(False, expected_message)

    def test_assert_option_raises_custom_exception_if_exception_is_passed(self):
        """:meth:`ConfigMapping.assert_option` allows raising custom exception."""
        with pytest.raises(SyntaxError):
            ConfigMapping.assert_option(False, SyntaxError())
