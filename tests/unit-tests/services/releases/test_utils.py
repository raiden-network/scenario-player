import pathlib
import filecmp

from contextlib import contextmanager
from typing import Tuple
from unittest import mock

import pytest

from requests import Response

from raiden.scenario_player.services.releases.utils import download_archive
from raiden.scenario_player.services.releases.utils import RaidenArchive
from raiden.scenario_player.services.releases.utils import RaidenBinary

from raiden.scenario_player.exceptions import ArchiveNotAvailableOnLocalMachine
from raiden.scenario_player.exceptions import BrokenArchive
from raiden.scenario_player.exceptions import InvalidArchiveLayout
from raiden.scenario_player.exceptions import InvalidArchiveType
from raiden.scenario_player.exceptions import InvalidReleaseVersion
from raiden.scenario_player.exceptions import TargetPathMustBeDirectory


class DownloadArchiveTestCase:

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_downloading_archive_for_release_which_does_not_exist_locally_fetches_archive_from_raiden_cloud(self, mock_get):
        CLOUD_STORAGE_URL = ''
        RELEASE_VERSION = ''
        EXPECTED_URL = f'{CLOUD_STORAGE_URL}/{RELEASE_VERSION}-linux_amd64.tar.gz'
        download_archive(RELEASE_VERSION)
        mock_get.assert_called_once_with(EXPECTED_URL)

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_function_is_idempotent_by_default(self, mock_get):
        RELEASE_VERSION = ''
        download_archive(RELEASE_VERSION)
        assert mock_get.call_count == 1

        download_archive(RELEASE_VERSION)
        assert not mock_get.call_count == 1

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_func_downloads_archive_again_if_param_cached_is_false(self, mock_get):
        download_archive(RELEASE_VERSION)
        mock_get.reset_mock()

        download_archive(RELEASE_VERSION, cached=False)
        mock_get.assert_called_once_with(EXPECTED_URL)

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_func_raises_InvalidReleaseVersion_if_it_cannot_be_found_on_raiden_cloud(self, mock_get):
        mock_resp = Response()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        with pytest.raises(InvalidReleaseVersion):
            download_archive('42')


class RaidenArchiveClassTestCase:

    @contextmanager
    @staticmethod
    def archive_constructor(root_dir: pathlib.Path, ext: str, folders: int=1, files: int=1, broken: bool=False) -> pathlib.Path:
        """Create an archive file.

        When used as a context manager, it will automatically clean up the file.

        :param ext:
            The archive type. If this is not ``zip`` or ``tar.gz`` we use zip and replace the ext
            with the given one. We assume that in this case, the file will not be opened - otherwise
            this will result in an error.
        :param folders: Number of folders to put into the archive.
        :param files: Number of files in each folder to create.
        :param broken:
            Whether or not to intentionally break the archive. This is achieved by usingthe opposite
            archive class of `ext`, and appending the extension to the resulting name.

        """
        archive_path = root_dir.joinpath('test-archive')
        archive_path.mkdir()

        # Create the folder structure to be archived.
        for i in range(folders):
            sub_dir = archive_path.joinpath(f'folder_{i}')
            sub_dir.mkdir()
            for j in range(files):
                sub_dir.joinpath(f'file-{j}').touch()

        # Pack the directory.
        # FIXME: This is a stub - Calling the respective classes is NOT syntactically correct!
        if ext == 'tar.gz':
            archive_file = Tarfile(root_dir)
        else:
            archive_file = Zipfile(root_dir)

        packed_path = archive_file.abspath()

        # Scramble the extensions, if requested.
        if broken:
            packed_path.rename(f'{packed_path.resolve()}.{"zip" if ext == "tar.gz" else "tar.gz"}')

        yield packed_path

    @contextmanager
    def create_valid_archive(self, root_dir, ext):
        yield self.archive_constructor(root_dir, ext)

    @contextmanager
    def create_invalid_archive_multiple_dirs(self, root_dir, ext):
        yield self.archive_constructor(root_dir, ext, folders=2)

    @contextmanager
    def create_invalid_archive_single_dir_multiple_files(self, root_dir, ext):
        yield self.archive_constructor(root_dir, ext, files=2)

    @contextmanager
    def create_broken_archive(self, root_dir, ext):
        yield self.archive_constructor(root_dir, ext, broken=True)

    @pytest.mark.parametrize('ext, uses_tarfile, uses_zipfile', [('tar.gz', True, False), ('zip', False, True)])
    @mock.patch("raiden.scneario_player.services.releases.utils.zipfile.Zipfile")
    @mock.patch("raiden.scneario_player.services.releases.utils.tarfile.Tarfile.open")
    def test_class_chooses_correct_open_function_depending_on_extension(self, mock_tarfile_open, mock_zipfile, ext, uses_tarfile, uses_zipfile, tmpdir_path):
        with self.create_valid_archive(tmpdir_path, ext) as packed_path:
            _ = RaidenArchive(packed_path)
            assert mock_tarfile_open.called is uses_tarfile
            assert mock_zipfile.called is uses_zipfile

    @pytest.mark.parametrize('ext, uses_tarfile, uses_zipfile', [('tar.gz', True, False), ('zip', False, True)])
    @mock.patch("raiden.scneario_player.services.releases.utils.zipfile.Zipfile.namelist")
    @mock.patch("raiden.scneario_player.services.releases.utils.tarfile.Tarfile.getnames")
    def test_unpack_chooses_correct_open_function_depending_on_extension(self, mock_tarfile_list, mock_zipfile_list, ext, uses_tarfile, uses_zipfile, tmpdir_path):
        with self.create_valid_archive(tmpdir_path, ext) as packed_path:
            archive = RaidenArchive(packed_path)
            archive.unpack(tmpdir_path.joinpath('unpacked'))
            assert mock_tarfile_list.called is uses_tarfile
            assert mock_zipfile_list.called is uses_zipfile

    def test_archive_unpack_returns_the_path_to_the_unpacked_binary(self, tmpdir_path):
        with self.create_valid_archive(tmpdir_path, 'zip') as packed_path:
            archive = RaidenArchive(packed_path)
            bin_path = archive.unpack(tmpdir_path)
            assert packed_path.parent().joinpath(packed_path.stem) == bin_path

    def test_class_raises_ArchiveNotVailableOnLocalMachine_exception_if_the_given_archive_path_does_not_exist(self):
        with pytest.raises(ArchiveNotAvailableOnLocalMachine):
            RaidenArchive(pathlin.Path('/does/not/exist.zip'))

    def test_class_raises_InvalidArchiveType_if_archive_is_not_zip_or_tar(self, tmpdir_path):
        with pytest.raises(InvalidArchiveType), self.create_valid_archive(tmpdir_path, '.archive') as archive_path:
            RaidenArchive(archive_path)

    @pytest,mark.parametrize('ext', ['zip', 'tar.gz'])
    def test_class_detects_invalid_archives_correctly(self, tmpdir_path, ext):
        """Archives must have exactly 1 directory, containing exactly 1 file (the raiden binary).

        Assert that this is detected correctly when instantiating a RaidenArchive class.
        """
        with pytest.raises(InvalidArchiveLayout), self.create_invalid_archive_multiple_dirs(tmpdir_path, ext) as archive_path:
            RaidenArchive(archive_path)

        with pytest.raises(InvalidArchiveLayout), self.create_invalid_archive_single_dir_multiple_files(tmpdir_path, ext) as archive_path:
            RaidenArchive(archive_path)

    @pytest,mark.parametrize('ext', ['zip', 'tar.gz'])
    def test_class_raises_BrokenArchive_exception_if_the_archive_cannot_be_read(self, tmpdir_path):
        with pytest.raises(BrokenArchive), self.create_broken_archive(tmpdir_path, 'zip') as archive_path:
            RaidenArchive(archive_path)


class RaidenBinaryClassTestCase:

    @contextmanager
    def create_bin_file(self, root_dir: pathlib.Path) -> pathlib.Path:
        bin_path = root_dir.joinpath('raiden-linux-v1.2.3')
        yield bin_path

    @contextmanager
    def create_bin_obj(self, root_dir: pathlib.Path) ->  Tuple[pathlib.Path, RaidenBinary]:
        with self.create_bin_file(root_dir) as bin_path:
            bin_obj = RaidenBinary(bin_path)
            yield bin_path, bin_obj

    @contextmanager
    def create_installed_bin_obj(self, root_dir: pathlib.Path) -> Tuple[pathlib.Path, RaidenBinary, pathlib.Path]:
        with self.create_bin_obj(root_dir) as (bin_path, bin_obj):
            install_path = pathlib.Path('./raiden-binary-class-tests/')
            install_path.mkdir(exist_ok=True)
            bin_obj.install()
            yield bin_path, bin_obj, install_path

    def test_class_raises_BinaryDoesNotExist_if_the_binary_path_does_not_exist(self):
        bin_path = pathlib.Path('/does/not/exist')
        with pytest.raises(RaidenBinaryDoesNotExist):
            RaidenBinary(bin_path)

    @mock.patch('raiden.scenario_player.services.releases.utils.pathlib.Path.chmod')
    def test_class_sets_correct_permissions_on_binary_after_extraction_from_archive(self, mock_chmod, tmpdir_path):
        with self.create_bin_obj(tmpdir_path) as (bin_path, bin_obj):
            mock_chmod.assert_called_once_with('755')
            assert bin_obj.executable is True
            assert bin_obj.installed is False

    def test_install_creates_a_symlink_at_given_location_by_default(self, tmpdir_path):
        with self.create_bin_file(tmpdir_path) as (bin_path, bin_obj):
            install_path = pathlib.Path('./install')
            install_path.mkdir(exist_ok=True)
            install_path = bin_obj.install(str(install_path))
            assert install_path.exists()
            assert install_path.is_symlink()
            assert bin_path == install_path.resolve()
            assert bin_obj.installed

    def test_install_creates_a_copy_of_the_binary_at_given_location_if_as_symlink_parameter_is_False(self, tmpdir_path):
        with self.create_bin_obj(tmpdir_path) as (bin_path, bin_obj):
            install_path = pathlib.Path('./install')
            install_path.mkdir(exist_ok=True)
            install_path = bin_obj.install(str(install_path), as_symlink=False)
            assert install_path.exists()
            assert install_path.is_symlink() is False
            assert filecmp.cmp(str(install_path), str(bin_path))
            assert bin_obj.installed

    def test_uninstall_removes_file_at_the_binarys_install_dir(self, tmpdir_path):
        with self.create_installed_bin_obj(tmpdir_path) as (bin_path, bin_obj, install_dir):
            assert install_path.exists() is True
            bin_obj.uninstall()
            assert install_path.exists() is False
            assert bin_path.exists() is True

    def test_remove_method_raises_a_CannotRemoveInstalledBinary_exception_if_binary_is_installed(self, tmpdir_path):
        with self.create_installed_bin_obj(tmpdir_path) as (_, bin_obj, __):
            with pytest.raises(CannotRemoveInstalledBinary):
                bin_obj.remove()

    def test_remove_method_deletes_the_binary_from_disk_if_not_installed(self, tmpdir_path):
        with self.create_bin_obj(tmpdir_path) as (bin_path, bin_obj):
            assert bin_obj.exists
            assert bin_obj.installed is False

            bin_obj.remove()

            assert bin_obj.installed is False
            assert bin_obj.exists_locally is False
            assert bin_path.exists() is False

    @mock.patch('raiden.scenario_player.services.releases.utils.RaidenBinary.remove')
    @mock.patch('raiden.scenario_player.services.releases.utils.RaidenBinary.uninstall')
    def test_purge_method_calls_uninstall_and_remove(self, bin_uninstall, bin_remove, tmpdir_path):
        with self.create_installed_bin_obj(tmpdir_path) as (_, bin_obj, __):
            bin_obj.purge()

            assert bin_uninstall.called
            assert bin_remove.called

            assert bin_obj.installed is False
            assert bin_obj.exists_locally is False

    def test_install_raises_a_BinaryDoesNotOnLocalMachine_if_bin_file_no_longer_exists(self, tmpdir_path):
        with self.create_bin_obj(tmpdir_path) as (bin_path, bin_obj):
            bin_path.unlink()
            assert bin_path.exists() is False
            with pytest.raises(BinaryDoesNotExistOnLocalMachine):
                bin_obj.install(tmpdir_path)

    def test_instance_can_be_created_from_a_dict_in_a_correct_format_using_its_from_dict_method(self, tmpdir_path):
        with self.create_installed_bin_obj(tmpdir_path) as (_, bin_obj, __):
            obj_dict = vars(bin_obj)
            loaded_bin_obj = RaidenBinary.from_dict(obj_dict)
            assert bin_obj == loaded_bin_obj

    def test_class_has_expected_attributes(self, tmpdir_path):
        with self.create_bin_obj(tmpdir_path) as (bin_path, bin_obj):
            assert vars(bin_obj).keys() == {'bin_path', 'install_path', 'version'}