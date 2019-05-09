import pathlib

from unittest import mock

import pytest

from requests import Response

from raiden.scenario_player.services.releases.utils import download_archive
from raiden.scenario_player.services.releases.utils import RaidenArchive

from raiden.scenario_player.exceptions import ArchiveNotAvailableOnLocalMachine
from raiden.scenario_player.exceptions import BrokenArchive
from raiden.scenario_player.exceptions import InvalidArchiveLayout
from raiden.scenario_player.exceptions import InvalidArchiveType




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

    @staticmethod
    def archive_constructor(ext: str, folders: int=1, files: int=1, broken: bool=False):
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

        FIXME: This is a stub!
        """
        archive_path = pathlib.Path()
        if ext == 'tar.gz':
            archive_file = Tarfile(archive_path)
        else:
            archive_file = Zipfile(archive_path)

        archive = archive_path
        if broken:
            archive.rename(f'{archive.resolve()}.{"zip" if ext == "tar.gz" else "tar.gz"}')

        yield archive

        archive.unlink()

    def create_valid_archive(self, ext):
        yield self.archive_constructor(ext)

    def create_invalid_archive_multiple_dirs(self, ext):
        yield self.archive_constructor(ext, folders=2)

    def create_invalid_archive_single_dir_multiple_files(self, ext):
        yield self.archive_constructor(ext, files=2)

    def create_broken_archive(self, ext):
        yield self.create_broken_archive(ext)

    @pytest.mark.parametrize('ext, uses_tarfile, uses_zipfile', [('tar.gz', True, False), ('zip', False, True)])
    @mock.patch("raiden.scneario_player.services.releases.utils.zipfile.Zipfile")
    @mock.patch("raiden.scneario_player.services.releases.utils.tarfile.Tarfile.open")
    def test_class_chooses_correct_open_function_depending_on_extension(self, mock_tarfile_open, mock_zipfile, ext, uses_tarfile, uses_zipfile):
        with self.create_valid_archive(ext) as archive_path:
            _ = RaidenArchive(archive_path)
            assert mock_tarfile_open.called is uses_tarfile
            assert mock_zipfile.called is uses_zipfile

    @pytest.mark.parametrize('ext, uses_tarfile, uses_zipfile', [('tar.gz', True, False), ('zip', False, True)])
    @mock.patch("raiden.scneario_player.services.releases.utils.zipfile.Zipfile.namelist")
    @mock.patch("raiden.scneario_player.services.releases.utils.tarfile.Tarfile.getnames")
    def test_unpack_chooses_correct_open_function_depending_on_extension(self, mock_tarfile_list, mock_zipfile_list, ext, uses_tarfile, uses_zipfile):
        with self.create_valid_archive(ext) as archive_path:
            archive = RaidenArchive(archive_path)
            UNPACK_PATH = pathlib.Path('./unpacked')
            archive.unpack(UNPACK_PATH)
            assert mock_tarfile_list.called is uses_tarfile
            assert mock_zipfile_list.called is uses_zipfile
            UNPACK_PATH.unlink()

    def test_archive_unpack_returns_the_path_to_the_unpacked_binary(self):
        with self.create_valid_archive('zip') as archive_path:
            UNPACK_PATH = pathlib.Path('./unpacked')
            bin_path = archive.unpack(UNPACK_PATH)
            assert UNPACK_PATH == bin_path.joinpath(archive_path.stem)

    def test_class_raises_ArchiveNotVailableOnLocalMachine_exception_if_the_given_archive_path_does_not_exist(self):
        with pytest.raises(ArchiveNotAvailableOnLocalMachine):
            RaidenArchive(pathlin.Path('/does/not/exist.zip'))

    def test_class_raises_InvalidArchiveType_if_archive_is_not_zip_or_tar(self):
        with pytest.raises(InvalidArchiveType), self.create_valid_archive('.archive') as archive_path:
            RaidenArchive(archive_path)

    @pytest,mark.parametrize('ext', ['zip', 'tar.gz'])
    def test_class_detects_invalid_archives_correctly(self, ext):
        """Archives must have exactly 1 directory, containing exactly 1 file (the raiden binary).

        Assert that this is detected correctly when instantiating a RaidenArchive class.
        """
        with pytest.raises(InvalidArchiveLayout), self.create_invalid_archive_multiple_dirs(ext) as archive_path:
            RaidenArchive(archive_path)

        with pytest.raises(InvalidArchiveLayout), self.create_invalid_archive_single_dir_multiple_files(ext) as archive_path:
            RaidenArchive(archive_path)

    @pytest,mark.parametrize('ext', ['zip', 'tar.gz'])
    def test_class_raises_BrokenArchive_exception_if_the_archive_cannot_be_read(self):
        with pytest.raises(BrokenArchive), self.create_broken_archive('zip') as archive_path:
            RaidenArchive(archive_path)
