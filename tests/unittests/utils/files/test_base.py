import pathlib

from unittest import mock
from os import PathLike
import pytest


from scenario_player.utils.files import ManagedFile
from scenario_player.exceptions.files import ReferenceDropped


@pytest.fixture
def tmp_src_fpath(tmp_path) -> pathlib.Path:
    fpath = tmp_path.joinpath('test_file')
    fpath.touch()
    return fpath


@pytest.fixture
def tmp_target_dir(tmp_path) -> pathlib.Path:
    fpath = tmp_path.joinpath('target')
    fpath.mkdir()
    return fpath


class TestManagedFile_properties:
    def test_exists_locally_property_detects_presence_of_managed_file_on_disk_correctly(self, tmp_src_fpath):
        instance = ManagedFile(tmp_src_fpath)

        assert tmp_src_fpath.exists() is True
        assert instance.exists_locally is True

        tmp_src_fpath.unlink()
        assert instance.exists_locally is False

    @mock.patch('scenario_player.utils.files.base.ManagedFile.update_file_references')
    def test_has_copies_property_correctly_assert_copy_presence_from_copies_attribute_of_instance(
            self, mock_update_refs, tmp_src_fpath):
        """The property :attr:`ManagedFile.has_copies` should check for the existence of
        any known, created copies for the managed file.

        We do this by checking if :attr:`ManagedFile.copies` is truthy. In order for that
        attribute to be a correct representation of the current state, we must assert
        that :meth:`ManagedFile.update_file_references` is called before returning a result.
        """
        instance = ManagedFile(tmp_src_fpath)

        mock_update_refs.assert_not_called()
        assert instance.copies == set()
        assert instance.has_copies is False
        mock_update_refs.assert_called_once()

        instance.copies.add('/path/to/test')
        mock_update_refs.reset_mock()

        assert instance.has_copies is True
        mock_update_refs.assert_called_once()

    @mock.patch('scenario_player.utils.files.base.ManagedFile.update_file_references')
    def test_has_symlinks_property_correctly_assert_copy_presence_from_symlinks_attribute_of_instance(
            self, mock_update_refs, tmp_src_fpath):
        """The property :attr:`ManagedFile.has_symlinks` should check for the existence of
        any known, created symlinks for the managed file.

        We do this by checking if :attr:`ManagedFile.symlinks` is truthy. In order for that
        attribute to be a correct representation of the current state, we must assert
        that :meth:`ManagedFile.update_file_references` is called before returning a result.
        """
        instance = ManagedFile(tmp_src_fpath)

        mock_update_refs.assert_not_called()
        assert instance.symlinks == set()
        assert instance.has_symlinks is False
        mock_update_refs.assert_called_once()

        instance.symlinks.add('/path/to/test')
        mock_update_refs.reset_mock()

        assert instance.has_symlinks is True
        mock_update_refs.assert_called_once()


class TestManagedFile_update_file_references_method:

    def test_yield_unchanged_symlinks_excludes_deleted_symlinks(self, tmp_src_fpath, tmp_target_dir):
        """If a symlink was deleted on disk, it should no be yielded by :meth:`ManagedFile.yield_unchanged_symlinks`."""
        instance = ManagedFile(tmp_src_fpath)

        instance.create_symlink(tmp_target_dir)
        assert set(instance.yield_unchanged_symlinks()) == {tmp_target_dir}

        tmp_target_dir.joinpath(tmp_src_fpath.name).unlink()
        assert set(instance.yield_unchanged_symlinks()) == set()

    def test_yield_unchanged_symlinks_excludes_modified_symlinks(self, tmp_src_fpath, tmp_target_dir):
        """If a symlink no longer points to :attr:`ManagedFile.path`, it should no be yielded
        by :meth:`ManagedFile.yield_unchanged_symlinks`."""
        instance = ManagedFile(tmp_src_fpath)

        instance.create_symlink(tmp_target_dir)
        assert set(instance.yield_unchanged_symlinks()) == {tmp_target_dir}

        # unlink the symlink, create a new one with an identical name but point to a different loation.
        tmp_target_dir.joinpath(tmp_src_fpath.name).unlink()
        another_file = tmp_target_dir.joinpath('wooha')
        another_file.touch()
        tmp_target_dir.joinpath(tmp_src_fpath.name).symlink_to(another_file)
        assert set(instance.yield_unchanged_symlinks()) == set()

    def test_yield_unchanged_copies_excludes_deleted_copies(self, tmp_src_fpath, tmp_target_dir):
        """If a hard-copy was deleted on disk, it should no be yielded by :meth:`ManagedFile.yield_unchanged_copies`."""
        instance = ManagedFile(tmp_src_fpath)

        instance.copy_to_dir(tmp_target_dir)
        assert set(instance.yield_unchanged_copies()) == {tmp_target_dir}

        tmp_target_dir.joinpath(tmp_src_fpath.name).unlink()
        assert set(instance.yield_unchanged_copies()) == set()

    def test_yield_unchanged_copies_excludes_copies_converted_to_symlinks(self, tmp_src_fpath, tmp_target_dir):
        """If a hard-copy was turned into a symlink on disk, it should no be yielded
        by :meth:`ManagedFile.yield_unchanged_copies`."""
        instance = ManagedFile(tmp_src_fpath)

        instance.copy_to_dir(tmp_target_dir)
        assert set(instance.yield_unchanged_copies()) == {tmp_target_dir}

        # unlink the copy, create a new one with an identical name but make it a symlink.
        tmp_target_dir.joinpath(tmp_src_fpath.name).unlink()
        tmp_target_dir.joinpath(tmp_src_fpath.name).symlink_to(tmp_src_fpath)

        assert set(instance.yield_unchanged_copies()) == set()

    @pytest.mark.parametrize(
        'generator_method, attr',
        argvalues=[
            (ManagedFile.yield_unchanged_copies, 'copies'),
            (ManagedFile.yield_unchanged_symlinks, 'symlinks'),
        ],
        ids=['yield_unchanged_copies()', 'yield_unchanged_symlinks()']
    )
    def test_reference_update_generator_sub_routines_warn_when_dropping_references(
            self, generator_method, attr, tmp_src_fpath, tmp_target_dir):
        """When we drop a reference, a warning is raised indicating the path we're dropping and from what attribute."""
        instance = ManagedFile(tmp_src_fpath)
        getattr(instance, attr).add(tmp_target_dir)

        expected_msg = f"Reference {tmp_target_dir.joinpath(tmp_src_fpath.name)} changed on disk - dropping it from '{instance}.{attr}'."

        with pytest.warns(ReferenceDropped):
            set(generator_method(instance))

    @pytest.mark.parametrize('generator_method', argvalues=['yield_unchanged_symlinks', 'yield_unchanged_copies'])
    def test_update_file_references_calls_yield_unchanged_generator(self, generator_method, tmp_src_fpath):
        """The method :meth:`ManagedFile.update_file_references` makes use of
        our generator sub-routines to detect changes."""
        with mock.patch(f'scenario_player.utils.files.base.ManagedFile.{generator_method}', return_value=iter([])) as mock_generator:
            instance = ManagedFile(tmp_src_fpath)
            instance.update_file_references()
            mock_generator.assert_called_once()


class TestManagedFileInterface:

    def test_class_checks_if_file_exists_on_instance_creation(self):
        """We can't manage files that do not exist.

        Raise a :exc:`FileNotFoundError` if path-like passed to the constructor does not exist.
        """
        with pytest.raises(FileNotFoundError):
            ManagedFile(pathlib.Path('/does/not/exist'))

    def test_copy_to_dir_copies_file_to_target(self, tmp_src_fpath, tmp_target_dir):
        """:meth:`ManagedFile.copy_to_dir` creates a hard-copy of the managed file in a target directory."""
        managed_file = ManagedFile(tmp_src_fpath)
        expected_fpath = tmp_target_dir.joinpath(tmp_src_fpath.name).resolve()
        assert expected_fpath.exists() is False

        managed_file.copy_to_dir(tmp_target_dir)
        assert expected_fpath.exists() is True
        assert expected_fpath.samefile(tmp_src_fpath) is False

    @pytest.mark.parametrize(
        argnames='method',
        argvalues=[
            ManagedFile.copy_to_dir,
            ManagedFile.create_symlink
        ],
        ids=['copy_to_dir()', 'create_symlink()'],
    )
    def test_creation_methods_raise_NotADirectoryError_exception_if_the_target_is_not_a_directory(
            self, method, tmp_src_fpath, tmp_target_dir):
        """Creating a symlink or hard-copy in a target directory requires the path
        to point to a directory, not a file.

        Raise a :exc:`NotADirectoryError` if this is not the case.
        """
        managed_file = ManagedFile(tmp_src_fpath)
        target = tmp_target_dir.joinpath('file_1')
        target.touch()
        assert target.is_file()
        with pytest.raises(NotADirectoryError):
            method(managed_file, target)

    def test_class_is_pathlike(self):
        """The :cls:`ManagedFile` class is path-like."""
        assert issubclass(ManagedFile, PathLike)

    @pytest.mark.parametrize('create_method', argvalues=[ManagedFile.create_symlink, ManagedFile.copy_to_dir])
    @mock.patch('scenario_player.utils.files.base.ManagedFile.update_file_references')
    def test_remove_from_dir_calls_update_reference_method(
            self, mock_update_refs, create_method, tmp_src_fpath, tmp_target_dir):
        """Assert that removing a file calls :meth:`ManagedFile.update_file_references` as well.

        Furthermore, assert that the method of creation of the file-to-be-removed is irrelevant.
        it should be called regardless of its type (symlinnk or hard-copy).
        """
        instance = ManagedFile(tmp_src_fpath)
        create_method(instance, tmp_target_dir)

        mock_update_refs.reset_mock()
        instance.remove_from_dir(tmp_target_dir)
        mock_update_refs.assert_called_once()

    def test_copy_to_dir_correctly_updates_reference_list_in_instance(
            self, tmp_src_fpath, tmp_target_dir):
        """The method :meth:`ManagedFile.copy_to_dir` assigns new references
        to :attr:`ManagedFile.copies`."""
        managed_file = ManagedFile(tmp_src_fpath)
        assert bool(managed_file.copies) is False
        managed_file.copy_to_dir(tmp_target_dir)
        assert tmp_target_dir in managed_file.copies
        assert len(managed_file.copies) == 1

    def test_create_symlink_updates_references_correctly(self, tmp_src_fpath, tmp_target_dir):
        """The method :meth:`ManagedFile.create_symlink` assigns new references to
         :attr:`ManagedFile.symlinks`."""

        managed_file = ManagedFile(tmp_src_fpath)
        assert bool(managed_file.symlinks) is False
        managed_file.create_symlink(tmp_target_dir)
        assert tmp_target_dir in managed_file.symlinks
        assert len(managed_file.symlinks) == 1

    def test_create_symlink_creates_a_symlink_in_target_dir_and_links_to_correct_path(
            self, tmp_src_fpath, tmp_target_dir):
        """The method :meth:`ManagedFile.create_symlink` does what it says on the tin.

        The symlink should point to the managed file at :attr:`ManagedFile.path`.
        """
        managed_file = ManagedFile(tmp_src_fpath)

        expected_created_file = tmp_target_dir.joinpath(tmp_src_fpath.name)
        assert expected_created_file.exists() is False

        managed_file.create_symlink(tmp_target_dir)
        assert expected_created_file.exists() is True
        assert expected_created_file.is_symlink() is True
        assert expected_created_file.samefile(tmp_src_fpath) is True

    def test_remove_from_dir_removes_copy_at_target(self, tmp_src_fpath, tmp_target_dir):
        """The method :meth:`ManagedFile.remove_from_dir` correctly removes hard-copies of
        the managed file from a given dir."""
        managed_file = ManagedFile(tmp_src_fpath)

        # Inject a tar path.
        tar_file = tmp_target_dir.joinpath(tmp_src_fpath.name)
        tar_file.touch()
        managed_file.copies.add(tmp_target_dir)

        assert managed_file.remove_from_dir(tmp_target_dir) is True
        assert tar_file.exists() is False
        assert tmp_target_dir not in managed_file.copies

    def test_remove_from_dir_removes_symlink_at_target(self, tmp_src_fpath, tmp_target_dir):
        """The method :meth:`ManagedFile.remove_from_dir` correctly removes symlinks of the
        managed file from a given dir."""
        managed_file = ManagedFile(tmp_src_fpath)

        # Inject a tar path.
        tar_file = tmp_target_dir.joinpath(tmp_src_fpath.name)
        tar_file.symlink_to(tmp_src_fpath)
        managed_file.symlinks.add(tmp_target_dir)

        assert managed_file.remove_from_dir(tmp_target_dir) is True
        assert tar_file.is_symlink() is False

    def test_remove_dir_returns_false_and_does_nothing_if_tar_dir_is_not_in_symlinks_or_copies_attr(
            self, tmp_src_fpath, tmp_target_dir):
        """Files that are not kept in the the :cls:`ManagedFile` class's `symlinks` or `copies`
        attributes trigger a no-op and return False."""
        managed_file = ManagedFile(tmp_src_fpath)

        # Bypass the ManagedFile interface and directly create the file
        target_file = tmp_target_dir.joinpath(tmp_src_fpath.name)
        target_file.touch()

        # Assert that the path is still not managed by the interface
        assert tmp_target_dir not in managed_file.copies
        assert tmp_target_dir not in managed_file.symlinks

        # Assert that calling .remove_from_dir exits with a no-op and returns False.
        assert managed_file.remove_from_dir(tmp_target_dir) is False
        assert tmp_target_dir.exists() is True
