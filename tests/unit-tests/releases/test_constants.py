from unittest import mock

import pytest

from scenario_player.releases import PLATFORM_SEPCIFIC_VARS


class TestPLATFORM_SEPCIFIC_VARS:

    @pytest.mark.parametrize(
        argnames=['os', 'expected_fname'],
        argvalues=[
            ('darwin', '_LATEST-macOS-x86_64.txt'),
            ('linux', '_LATEST-linux-x86_64.txt'),
            ('win32', '_LATEST-linux-x86_64.txt'),
            ('cygwin', '_LATEST-linux-x86_64.txt'),
        ], ids=['MacOS', 'Linux', 'Windows', 'Windows Cygwin']
    )
    @mock.patch('scenario_player.releases.sys')
    def test_latest_file_name_is_constructed_correctly_on_all_platforms(
            self, mock_sys, os, expected_fname):
        mock_sys.configure_mock(platform=os)
        assert PLATFORM_SEPCIFIC_VARS.latest_file_name() == expected_fname

    @pytest.mark.parametrize(
        argnames=['os', 'expected_fname'],
        argvalues=[
            ('darwin', 'raiden-v{version}-macOS-x86_64.zip'),
            ('linux', 'raiden-v{version}-linux-x86_64.tar.gz'),
            ('win32', 'raiden-v{version}-linux-x86_64.tar.gz'),
            ('cygwin', 'raiden-v{version}-linux-x86_64.tar.gz'),
        ], ids=['MacOS', 'Linux', 'Windows', 'Windows Cygwin']
    )
    @mock.patch('scenario_player.releases.sys')
    def test_achive_name_template_is_constructed_correctly_on_all_platforms(
            self, mock_sys, os, expected_fname):
        mock_sys.configure_mock(platform=os)
        assert PLATFORM_SEPCIFIC_VARS.archive_name_template() == expected_fname
