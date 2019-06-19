import pathlib

from unittest import mock

import pytest

from scenario_player.exceptions.files import BinaryNotInstalled, BinaryNotInstalledInDirectory
from scenario_player.utils.files import RaidenBinary


RELEASE_VERSION = 'v900.134.2'


@pytest.fixture
def dummy_bin(tmp_path) -> pathlib.Path:
    p = tmp_path.joinpath(RELEASE_VERSION)
    p.touch()
    return p


class TestRaidenBinary:

    def test_install_dirs_is_union_of_copies_and_symlinks_attributes(self, dummy_bin):
        instance = RaidenBinary(dummy_bin)
        instance.symlinks.add('/path/to/a')
        instance.copies.add('/path/to/b')
        assert instance.install_dirs == {'/path/to/a', '/path/to/b'}

    def test_installed_property_returns_correct_boolean_value_depending_install_dirs_property(self, dummy_bin):
        instance = RaidenBinary(dummy_bin)

        assert instance.installed is False

        instance.copies.add('/path/to/a')
        assert instance.installed is True

    def test_is_executable_correctly_checks_file_permissions_of_the_managed_binary(self, dummy_bin):
        instance = RaidenBinary(dummy_bin)

        dummy_bin.chmod('600')
        assert instance.is_executable is False

        dummy_bin.chmod('700')
        assert instance.is_executable is True

    @mock.patch('scenario_player.utils.files.binary.RaidenBinary.create_symlink')
    def test_install_calls_create_symlink_by_default(self, mock_create_symlink, dummy_bin, tmp_path):
        instance = RaidenBinary(dummy_bin)
        instance.install(install_dir=tmp_path)
        mock_create_symlink.assert_called_once()

    @mock.patch('scenario_player.utils.files.binary.RaidenBinary.copy_to_dir')
    def test_install_calls_copy_to_dir_if_as_symlink_is_false(self, mock_copy_to_dir, dummy_bin, tmp_path):
        instance = RaidenBinary(dummy_bin)
        instance.install(install_dir=tmp_path, as_symlink=False)
        mock_copy_to_dir.assert_called_once()

    @mock.patch('scenario_player.utils.files.binary.RaidenBinary.remove_dir')
    def test_uninstall_removes_all_created_copies_and_symlinks_by_default(self, mock_rm_dir, dummy_bin, tmp_path):
        instance = RaidenBinary(dummy_bin)
        instance.install(tmp_path.joinpath('symlinks'))
        instance.install(tmp_path.joinpath('copies'), as_symlink=False)

        assert len(isntance.install_dirs)
        instance.uninstall()
        assert mock_rm_dir.call_count == 2
        assert instance.install_dirs == set()

    def test_uninstall_raises_BinaryNotINstalledInDirectory_if_install_dirs_is_not_empty_but_target_dir_is_not_in_it(
            self, dummy_bin, tmp_path):
        instance = RaidenBinary(dummy_bin)
        instance.copies.add(tmp_path.joinpath('whatever'))
        assert instance.install_dirs
        with pytest.raises(BinaryNotInstalledInDirectory):
            instance.uninstall(tmp_path)

    def test_uninstall_raises_BinaryNotINstalled_if_install_dirs_is_empty(self, dummy_bin, tmp_path):
        instance = RaidenBinary(dummy_bin)
        assert not instance.install_dirs
        with pytest.raises(BinaryNotInstalled):
            instance.uninstall(tmp_path)
