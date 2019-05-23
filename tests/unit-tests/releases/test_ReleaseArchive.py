import pathlib

from contextlib import contextmanager
from unittest import mock

import pytest
from scenario_player import releases
from scenario_player.releases import ReleaseArchive


@contextmanager
def assert_does_not_raise(exception=BaseException):
    try:
        yield
    except exception:
        raise pytest.fail("DID RAISE {0}".format(exception))


class TestReleaseArchive:

    @mock.patch('scenario_player.releases.ReleaseArchive.validate')
    def test_validate_is_called_on_init(self, mock_validate, single_file_zip):
        ReleaseArchive(pathlib.Path(single_file_zip.filename))
        mock_validate.assert_called_once()

    @mock.patch('scenario_player.releases.zipfile.Zipfile')
    def test_init_with_path_to_zip_calls_zipfile_open_method(self, mock_open, single_file_zip):

        release_archive = ReleaseArchive(pathlib.Path(single_file_zip.filename))
        mock_open.assert_called_once_with(pathlib.Path(single_file_zip.filename), 'r')
        assert release_archive._context == mock_open

    @mock.patch('scenario_player.releases.Tarfile.open')
    def test_init_with_path_to_tar_calls_tarfile_open_method(self, mock_open, single_file_tar):
        release_archive = ReleaseArchive(pathlib.Path(single_file_tar.name))
        mock_open.assert_called_once_with(pathlib.Path(single_file_tar.name), 'r:*')
        assert release_archive._context == mock_open

    @mock.patch('scenario_player.releases.ZipFile.namelist')
    def test_files_property_uses_zipfile_namelist_if_archive_ends_with_zip(self, mock_get_files, single_file_zip):
        release_archive = ReleaseArchive(pathlib.Path(single_file_zip.filename))
        release_archive.files
        mock_get_files.assert_called_once()

    @mock.patch('scenario_player.releases.Tarfile.getnames')
    def test_files_property_uses_tarfile_getnames_if_archive_ends_with_gz(self, mock_get_files, single_file_tar):
        release_archive = ReleaseArchive(pathlib.Path(single_file_tar.name))
        release_archive.files
        mock_get_files.assert_called_once()

    def test_binary_property_returns_file_in_archive_at_index_0(self, single_file_tar):
        release_archive = ReleaseArchive(pathlib.Path(single_file_tar.name))
        assert release_archive.binary == single_file_tar.getnames()[0]

    def test_validate_raises_ValueError_fails_for_multifile_zip_archives(self, multi_file_zip):
        with pytest.raises(ValueError):
            ReleaseArchive(pathlib.Path(multi_file_zip.filename))

    def test_validate_raises_ValueError_fails_for_multifile_tar_archives(self, multi_file_tar):
        with pytest.raises(ValueError):
            ReleaseArchive(pathlib.Path(multi_file_tar.name))

    def test_validate_succeeds_silently_for_single_file_zip_archives(self, single_file_zip):
        with assert_does_not_raise():
            ReleaseArchive(pathlib.Path(single_file_zip.filename))

    def test_validate_succeeds_silently_for_single_file_tar_archives(self, single_file_tar):
        with assert_does_not_raise():
            ReleaseArchive(pathlib.Path(single_file_tar.name))

    @mock.patch('scenario_player.releases.ReleaseArchive.files', new_callable=mock.PropertyMock)
    def test_unpack_calls_extractall_of_context_with_expected_parameters_and_sets_bits(self, mock_files, single_file_zip):
        mock_files.return_value = ['A file in the archive']
        archive = ReleaseArchive(pathlib.Path(single_file_zip.filename))
        archive._context = mock.Mock()
        mock_path = mock.Mock(spec=pathlib.Path)
        assert archive.unpack(mock_path) == mock_path
        archive._context.extractall.assert_called_once_with(members=[archive.binary], path=mock_path)
        mock_path.chmod.assert_called_once_with(0o770)

    def test_close_method_closes_context_if_available(self, single_file_zip):
        archive = ReleaseArchive(pathlib.Path(single_file_zip.filename))
        mock_obj = mock.MagicMock()
        mock_obj.configure_mock(close=mock_obj)

        archive._context = mock_obj
        archive.close()
        mock_obj.close.assert_called_once()

        mock_obj.reset_mock()
        archive._context = None
        archive.close()
        assert mock_obj.close.called is False

