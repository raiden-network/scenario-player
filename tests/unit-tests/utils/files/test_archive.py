"""Test harness for the :mod:`scenario_player.utils.files.archive` module."""
import pathlib
import tarfile

from zipfile import ZipFile


from scenario_player.utils.files import RaidenArchive
from scenario_player.exceptions import ArchiveNotAvailableOnLocalMachine
from scenario_player.exceptions import BrokenArchive
from scenario_player.exceptions import InvalidArchiveLayout
from scenario_player.exceptions import InvalidArchiveType


from unittest import mock

import pytest
from pytest import mark
from requests import Response

from scenario_player.utils.files import construct_archive_fname, download_archive
from scenario_player.utils.files.constants import ARCHIVE_FNAME_TEMPLATE, CLOUD_STORAGE_URL

from scenario_player.exceptions import InvalidReleaseVersion


class MockResponse(Response):
    def __init__(self, json_func_return_value=None):
        self._json = json_func_return_value or {}
        super(MockResponse, self).__init__()

    def json(self, *args, **kwargs):
        return self._json


TEST_VERSION = 'v900.134.2'


@pytest.fixture
def raiden_dir(tmp_path) -> pathlib.Path:
    """A test-scoped `.raiden` directory, for usage with tests that require it.

    It's a good idea to use :func:`unitest.mock.patch('pathlib.Path.home')`
    and set the mock's return value to the `tmp_path` fixture's path.

    This automatically points the scenario_player classes and functions to
    `<temporary_dir>/.raiden` for each test.

    Using a broader scope than unit-tests is possible, but beware that this entails
    clean-up after tests, since files will be persisted between them, which may
    lead to false positives (or negatives).
    """
    raiden_dir = tmp_path.joinpath('.raiden')
    raiden_dir.mkdir()
    return raiden_dir


@pytest.fixture
def archive_factory(tmp_path):
    """Factory for all kinds of Raiden Release archives.

    The factory allows the creation of various archive configurations.


    Creating single-file archives::

        >>>archive = archive_factory('zip')
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.zip')
        >>>zipfile.ZipFile(archive).namelist()
        /<tmp_path fixture directory>/file-1

        >>>archive_factory('tar.gz')
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.tar.gz')
        >>>tarfile.open(archive).getnames()
        /<tmp_path fixture directory>/file-1

    Creating an archive with multiple files and no sub-directories::

        >>>archive = archive_factory('zip', files=3)
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.zip')
        >>>zipfile.ZipFile(archive).namelist()
        /<tmp_path fixture directory>/file-1
        /<tmp_path fixture directory>/file-2
        /<tmp_path fixture directory>/file-3

        >>>archive_factory('tar.gz', files=2)
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.tar.gz')
        >>>tarfile.open(archive).getnames()
        /<tmp_path fixture directory>/file-1
        /<tmp_path fixture directory>/file-2

    Creating an archive with multiple files in multiple sub-directories::

        >>>archive = archive_factory('zip', folders=2, files=3)
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.zip')
        >>>zipfile.ZipFile(archive).namelist()
        /<tmp_path fixture directory>/folder_1/file-1
        /<tmp_path fixture directory>/folder_1/file-2
        /<tmp_path fixture directory>/folder_1/file-3
        /<tmp_path fixture directory>/folder_2/file-1
        /<tmp_path fixture directory>/folder_2/file-2
        /<tmp_path fixture directory>/folder_2/file-4

        >>>archive_factory('tar.gz', folders=2, files=2)
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.tar.gz')
        >>>tarfile.open(archive).getnames()
        /<tmp_path fixture directory>/folder_1/file-1
        /<tmp_path fixture directory>/folder_1/file-2
        /<tmp_path fixture directory>/folder_2/file-1
        /<tmp_path fixture directory>/folder_2/file-2

    Creating an archive with empty folders::

        >>>archive = archive_factory('zip', folders=2, files=0)
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.zip')
        >>>zipfile.ZipFile(archive).namelist()
        /<tmp_path fixture directory>/folder_1/
        /<tmp_path fixture directory>/folder_2/

        >>>archive_factory('tar.gz', folders=2, files=0)
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.tar.gz')
        >>>tarfile.open(archive).getnames()
        /<tmp_path fixture directory>/folder_1/
        /<tmp_path fixture directory>/folder_2/

    Creating a scrambled archive, which will raise an error on opening;
    can be used to simulate corrupt archives::

        >>>archive = archive_factory('tar.gz', ext='zip')
        >>>archive
        PosixPath('/<tmp_path fixture directory>/test-archive.tar.gz.zip')
        >>>zipfile.ZipFile(archive)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "/usr/local/lib/python3.7/zipfile.py", line 1222, in __init__
            self._RealGetContents()
          File "/usr/local/lib/python3.7/zipfile.py", line 1289, in _RealGetContents
            raise BadZipFile("File is not a zip file")
        zipfile.BadZipFile: File is not a zip file

        >>>archive = archive_factory('zip', ext='.tar.gz')
        >>>tarfile.open(archive)

        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "/usr/local/lib/python3.7/tarfile.py", line 1578, in open
            raise ReadError("file could not be opened successfully")
        tarfile.ReadError: file could not be opened successfully
    """
    def archive_constructor(compression: str, scramble: bool=False, folders: int=0, files: int=1):
        """Return an archive with the given options.

        For example usages, see the docstring of the :func:`archive_factory` fixture.

        :param compression:
            The compression method to use. May be one of (`zip`, `tar.gz`)
        :param scramble:
            If this is `True`, we purposely corrupt the archive, rendering it
            unreadable.
        :param folders: Number of folders to put into the archive.
        :param files: Number of files in each folder to create.
        """
        def create_n_files(n, path):
            for i in range(n):
                path.joinpath(f'file-{i}').touch()

        # Create the folder structure to be archived.
        for i in range(folders):
            sub_dir = tmp_path.joinpath(f'folder_{i}')
            sub_dir.mkdir()

        # Create the desired number of files desired in each folder.
        # If there are no folders, we create it in the archive_path
        if folders > 0:
            for path in tmp_path.iterdir():
                if path.is_dir():
                    create_n_files(files, path)
        else:
            create_n_files(files, tmp_path)

        def pack_archive_using(method):
            for path in archive_path.iterdir():
                if path.endswith(('.tar.gz', '.zip')):
                    method(path)

        archive_path = tmp_path.joinpath('test-archive')
        # Pack the directory.
        if compression == 'tar.gz':
            archive_path = archive_path.withname('test-archive.tar.gz')
            with tarfile.open(tmp_path.joinpath('.tar.gz'), mode='x:gz') as archive:
                pack_archive_using(archive.add)
        else:
            archive_path = archive_path.withname('test-archive.zip')
            with ZipFile(tmp_path.joinpath('test-archive.zip'), 'x') as archive:
                pack_archive_using(archive.write)

        def scramble_archive(path):
            with path.open('wb') as f:
                f.write('Corrupting this archive. Oh what fun this is.')

        if scramble:
            scramble_archive(archive_path)
        return archive_path
    return archive_constructor


@mark.parametrize(
    argnames='arch, expected_arch',
    argvalues=[
        pytest.param(*('i368', ''), marks=mark.xfail),
        ('x86_64', ''),
        pytest.param(*('armv6', ''),marks=mark.xfail),
        pytest.param(*('armv7', ''), marks=mark.xfail),
    ],
    ids=['32-Bit', '64-bit', 'ARMv6', 'ARMv7'],
)
@pytest.mark.parametrize(
    argnames='platform, expected_platform, expected_ext',
    argvalues=[
        ('linux','linux', 'tar.gz'),
        ('darwin','MacOS', 'zip'),
        pytest.param(*('windows', 'win', 'zip'), marks=mark.xfail),
        pytest.param(*('cygwin', 'cygwin', 'zip'), marks=mark.xfail),
    ],
    ids=['Linux', 'MacOS', 'Windows', 'Windows - Cygwin'],
)
@mock.patch('scenario_player.utils.files.sys')
@mock.patch('scenario_player.utils.files.os.uname')
def test_archive_fname_constructor_creates_expected_archive_filenames(
        mock_uname, mock_sys,
        platform, expected_platform, expected_ext,
        arch, expected_arch,
):
    """Assert the function returns the correct platform/arch/extension combination, depending on the respective configuration."""
    mock_sys.configure_mock(platform=platform)
    # Mock the return value of os.uname() - only model should be relevant (index `4`),
    # the other fields should be ignored.
    mock_uname.return_value = (None, None, None, None, arch)

    # Construct the expected url to be called when executing :func:`download_archive`
    expected_archive_fname = ARCHIVE_FNAME_TEMPLATE.format(
        version=TEST_VERSION,
        platform=expected_platform,
        arch=expected_arch,
        ext=expected_ext
    )
    assert expected_archive_fname == construct_archive_fname(TEST_VERSION)


class TestDownloadArchive:

    def test_archive_fname_template_is_expected_string(self):
        assert ARCHIVE_FNAME_TEMPLATE == "{version}-{platform}_{arch}.{ext}"

    def test_cloud_url_is_expected_address(self):
        assert CLOUD_STORAGE_URL == 'http://cloud.raiden.network/'

    @mock.patch('scenario_player.utils.files.requests.get', return_value=MockResponse())
    @mock.patch('scenario_player.utils.files.pathlib.Path.home')
    def test_downloading_archive_for_release_which_does_not_exist_locally_fetches_archive_from_raiden_cloud(
            self,
            mock_home, mock_get,
            raiden_dir, tmp_path,
    ):
        """Assert that archives are downloaded from the expected URL with correct version and architecture,
        if they do not exist locally."""
        # Point the scenario player to the test's temp dir to look for a .raiden folder
        mock_home.return_value = tmp_path
        # Mock the return value of os.uname() - only model should be relevant (index `4`),
        # the other fields should be ignored.

        archive_fname = construct_archive_fname(TEST_VERSION)
        expected_url = CLOUD_STORAGE_URL + archive_fname

        assert raiden_dir,joinpath(archive_fname).exists() is False

        download_archive(TEST_VERSION)

        mock_get.assert_called_once_with(expected_url)

    @mock.patch('scenario_player.utils.files.requests.get', return_value=MockResponse())
    def test_function_is_idempotent_by_default(self, mock_get):
        """Calling the function twice in a row only downloads the archive once by default.

        Since the file should already exist locally after the first run, the second run
        should simply return with a no-op.
        """
        download_archive(TEST_VERSION)
        assert mock_get.call_count == 1
        mock_get.reset_mock()

        download_archive(TEST_VERSION)
        assert not mock_get.called

    @mock.patch('scenario_player.utils.files.pathlib.Path.home')
    @mock.patch('scenario_player.utils.files.requests.get', return_value=MockResponse())
    def test_func_downloads_archive_again_if_param_cached_is_false(self, mock_get, mock_home, raiden_dir, tmp_path):
        """Passing `cached=False` should cause :func:`download_archive` to ignore locally existing archives that match the version requested."""
        mock_home.return_value = tmp_path

        local_file = raiden_dir.joinpath('downloads', construct_archive_fname(TEST_VERSION))
        local_file.touch()

        download_archive(TEST_VERSION, cached=False)
        mock_get.assert_called_once_with(CLOUD_STORAGE_URL + construct_archive_fname(TEST_VERSION))

    @mock.patch('scenario_player.utils.files.requests.get')
    def test_func_raises_InvalidReleaseVersion_if_it_cannot_be_found_on_raiden_cloud(self, mock_get):
        mock_resp = MockResponse()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        with pytest.raises(InvalidReleaseVersion):
            download_archive('42')


class TestRaidenArchive:

    @pytest.mark.parametrize(
        argnames='compression, open_method, list_method, extract_method',
        argvalues=[
            ('tar.gz', tarfile.open, tarfile.TarFile.getnames, tarfile.TarFile.extractall),
            ('zip', ZipFile, ZipFile.namelist, ZipFile.extractall),
        ],
        ids=['Tar Archive', 'Zip Archive'],
    )
    def test_detect_compression_chooses_correct_methods_for_archive_access(
            self, compression, open_method, list_method, extract_method, archive_factory):
        """The method should choose the correct methods for interacting with the archive file.

        These should then be stored at the adequate attribute of the :cls:`RaidenArchive` instance.
        """
        archive_path = archive_factory(compression)
        instance = RaidenArchive(archive_path)
        instance.detect_compression()
        assert instance._open == open_method
        assert instance._list == list_method
        assert instance._extract == extract_method

    @pytest.mark.parametrize(
        argnames='instance_method',
        argvalues=[RaidenArchive.__enter__, RaidenArchive.open, RaidenArchive.list, RaidenArchive.extract],
        ids=['.__enter__()', '.open()', '.list()', '.extract(target_path)'],
    )
    @mock.patch('scenario_player.utils.files.RaidenArchive.detect_compression')
    def test_detect_compression_is_called_when_interacting_with_the_archive_file_method(
            self, mock_detect, instance_method, tmp_path):
        """Interacting with an archive requires the proper library and methods; ensure these are fetched before accessing the archive."""
        archive_path = archive_factory('tar.gz')
        instance = RaidenArchive(archive_path)
        try:
            instance_method(instance)
        except ValueError:
            # Likely needs a path parameter, pass one and try again.
            instance_method(instance, tmp_path)

        mock_detect.assert_called_once()

    @pytest.mark.parametrize(
        argnames='attr, instance_method',
        argvalues=[('_open', RaidenArchive.open), ('_list', RaidenArchive.list), ('_extract', RaidenArchive.extract)],
        ids=['open', 'list', 'extract']
    )
    def test_interacting_with_the_internal_archive_uses_corresponding_method_stored_at_the_internal_underscored_attr(
            self, attr, instance_method, archive_factory):
        """When calling methods on the class that require interaction with the archive file, ensure it uses the
        correct internally stored methods to access the archive.

        They are stored in a underscored-attribute with the otherwise same name as the method.
        For example, :meth:`RaidenArchive.open` would try to call the :attr:`RaidenArchive._open`.

        ..Note::

            The underscored attributes are populated by the :meth:`RaidenArchive.detect_compression`
            method, which is **not** under test here.
        """
        archive_path = archive_factory('tar.gz')
        instance = RaidenArchive(archive_path)
        mock_method = mock.MagicMock()
        setattr(instance, attr, mock_method)
        instance_method(instance)
        mock_method.assert_called_once()

    def test_archive_unpack_returns_the_path_to_the_unpacked_binary(self, archive_factory, tmp_path):
        """Unpacking an archive using :meth:`RaidenArchive.unpack` returns a :cls:`pathlib.Path` object
        pointing to the unpacked archive."""
        archive_path = archive_factory('tar.gz')
        archive = RaidenArchive(archive_path)
        target_path = tmp_path.joinpath('download')
        target_path.mkdir()
        bin_path = archive.unpack(target_path)
        assert target_path.joinpath(archive_path.stem) == bin_path

    def test_class_raises_ArchiveNotVailableOnLocalMachine_exception_if_the_given_archive_path_does_not_exist(self):
        """We can't manage a file that does not exist - ensure we fail expressively on instantation when this is the case."""
        with pytest.raises(ArchiveNotAvailableOnLocalMachine):
            RaidenArchive(pathlib.Path('/does/not/exist.zip'))

    def test_detect_compression_raises_InvalidArchiveType_if_the_archive_compression_is_not_supported(
            self, archive_factory):
        """We cannot possibly support every kind of archive type - let's make sure we fail expressively.

        Calling :meth:`RaidenArchive.detect_compression()` should raise a
        :exc:`InvalidArchiveType` exception.
        """
        archive_path = archive_factory('tar.gz', scramble=True)
        with pytest.raises(InvalidArchiveType):
            RaidenArchive(archive_path).detect_compression()

    @pytest.mark.parametrize(
        argnames='archive_config, should_raise',
        argvalues=[
            ({'files': 1, 'folders': 0}, False),
            ({'files': 2}, True),
            ({'folders': 2}, True),
            ({'files': 0, 'folders': 0}, True),
        ],
        ids=[
            'valid archive',
            'invalid archive - multiple files',
            'invalid archive - multiple directories',
            'invalid archives - empty archive'
        ],
    )
    @pytest.mark.parametrize('compression', argvalues=['tar.gz', 'zip'], ids=['.tar.gz', '.zip'])
    def test_validate_archive_detects_invalid_archives_correctly(
            self, compression, archive_config, should_raise,  archive_factory):
        """Archives must have exactly 0 directories and contain exactly 1 file (the raiden binary)."""
        archive_path = archive_factory(compression, **archive_config)
        instance = RaidenArchive(archive_path)
        try:
            with pytest.raises(InvalidArchiveLayout):
                instance.validate_archive()
        except AssertionError:
            if should_raise:
                # We expected InvalidArchiveLayout to be raised, according to parametrization.
                raise
            # parametrize says the function not raising InvalidArchiveLayout is ok.
            return

    @pytest.mark.parametrize('scrambled', argvalues=[True, False], ids=['Scrambled', 'Not Scrambled'])
    @pytest.mark.parametrize('compression', ['zip', 'tar.gz'])
    def test_open_method_raises_BrokenArchive_exception_if_the_archive_cannot_be_read(
            self, compression, scrambled, archive_factory):
        """Sometimes archives are corrupted. Let's make sure we fail expressively
         when trying to open such a file.

        This assumes that the archive was previously not corrupted, i.e. there
        was no :exc:`InvalidArchiveType` exception thrown when calling
        :meth:`RaidenArchive.detect_compression`.
        """
        archive_path = archive_factory(compression, scramble=scrambled)
        instance = RaidenArchive(archive_path)
        try:
            with pytest.raises(BrokenArchive):
                instance.open()
        except AssertionError:
            if scrambled:
                # We expected BrokenArchive to be raised, since the archive was scrambled.
                raise
            # The archive was not scrambled, hence this AssertionError is expected.
            return
