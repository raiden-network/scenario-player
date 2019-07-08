from unittest import mock

import pytest

from scenario_player.utils.files.mixins import (
    VersionedMixin,
    ArchitectureSpecificMixin,
    PlatformSpecificMixin,
)
from scenario_player.utils.files.parsing import parse_architecture, parse_platform, parse_version


BIN_TEMPLATE = "raiden_{version}"
ARCHIVE_TEMPLATE = BIN_TEMPLATE + ".{ext}"


@pytest.mark.parametrize(
    'mixin, prop_name, parse_func',
    argvalues=[
        (VersionedMixin, 'version', parse_version),
        (ArchitectureSpecificMixin, 'architecture', parse_architecture),
        (PlatformSpecificMixin, 'platform', parse_platform),
    ],
)
def test_mixin_property_calls_expected_parsing_function(mixin, prop_name, parse_func, tmp_path):
    with mock.patch(f'scenario_player.utils.files.mixins.{parse_func.__name__}') as mocked_func:
        class Mixed(mixin):
            def __init__(self, path):
                self.path = path

        instance = Mixed(tmp_path)
        getattr(instance, prop_name)
        mocked_func.assert_called_once_with(tmp_path)
