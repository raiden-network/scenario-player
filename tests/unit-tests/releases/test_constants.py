from unittest import mock

import pytest

from scenario_player.releases import RELEASE_ARCHIVE_NAME_TEMPLATE, RAIDEN_RELEASES_LATEST_FILE


class TestPlatformSepcificConstants:

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
    def test_RAIDEN_RELEASE_LATEST_FILE_name_is_constructed_correctly_on_all_platforms(
            self, mock_sys, os, expected_fname):
        mock_sys.configure(platform=os)
        assert RAIDEN_RELEASES_LATEST_FILE == expected_fname


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
    def test_RAIDEN_ARCHIVE_NAME_TEMPLATE_is_constructed_correctly_on_all_platforms(
            self, mock_sys, os, expected_fname):
        mock_sys.configure(platform=os)
        assert RELEASE_ARCHIVE_NAME_TEMPLATE == expected_fname
