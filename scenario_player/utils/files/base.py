import pathlib
import shutil

from os import PathLike
from typing import Iterable, Generator, Optional, Union
from scenario_player.exceptions.files import CannotImplicitlyChangeFileType

PathList = Iterable[Union[pathlib.Path, PathLike]]


class ManagedFile(PathLike):
    """File management interface for generic files.

    Takes care of copying the file to target directories using :meth:`.copy_to_dir`.

    Also allows creating symlinks instead of copies, using :meth:`.create_symlink`.

    Removes copies and symlinks created via the interface with :meth:`.remove`.

    Copies and symlinks will always have the same name as the :attr:`.path.name` of the instance's
    managed file::

        >>>from pathlib import Path
        >>>ManagedFile(Path('/myfile-123')).create_symlink(Path('/target_folder'))
        PosixPath('/target_folder/'myfile-123)

    It's not possible to change the name of the created file using the interface.


    ..Note::

        This class only allows creating copies of and symlinks to the managed file
        at :attr:`.path`. In addition, only copies and symlinks created with this
        interface may be removed using :meth:`.remove`. Attempting to remove
        any other file using an :cls:`pathlib.Path` object pointing to the file
        directly, will raise a :exc:`NotADirectoryError` exception.

        This is a **feature** of the interface, not a limitation.

    The :cls:`ManageFile` instances can be deserialized into a :cls:`dict` using
    :meth:`as_dict`. This can in turn be passed to the class constructor:

        >>>mf = ManagedFile(Path("/file-1"))
        >>>mf.copy_to_dir(Path('/folder'))
        >>>mf.as_dict()
        {'path': '/file-1', 'existing_copies': ['/folder/', 'existing_symlinks': []])}
        >>>ManagedFile(**mf.as_dict())

    """
    def __init__(
            self,
            path: Union[pathlib.Path, PathLike],
            existing_symlinks: Optional[PathList]=None,
            existing_copies: Optional[PathList]=None
    ) -> None:
        self.path = pathlib.Path(path).absolute()
        if not self.path.exists():
            raise FileNotFoundError(path)

        symlinks = [pathlib.Path(copy) for copy in (existing_symlinks or [])]
        copies = [pathlib.Path(copy) for copy in (existing_copies or [])]

        self.copies = set(copies)
        self.symlinks = set(symlinks)

    def __fspath__(self):
        return self.path.__fspath__()

    @property
    def exists_locally(self) -> bool:
        """Whether or not the managed file exists on the local machine."""
        return self.path.exists()

    @property
    def has_copies(self) -> bool:
        """Whether or not the managed file has copies created via this interface."""
        return bool(self.copies)

    @property
    def has_symlinks(self) -> bool:
        """Whether or not the managed file has symlinks created via this interface."""
        return bool(self.symlinks)

    def as_dict(self):
        """Dump the class to a loadable kwargs dict for the class constructor."""
        return {
            'path': str(self.path),
            'existing_symlinnks': [str(symlink) for symlink in self.symlinks],
            'existing_copies': [str(copy) for copy in self.copies],
        }

    def yield_unchanged_copies(self) -> Generator[pathlib.Path, None, None]:
        """Check each element in :attr:`.copies` for on-disk changes.

        If the file no longer exists or was converted to a symlink, we drop the
        reference to it.

        If we drop a reference, we log a warning.

        If the copy is unchanged and valid, we yield it.
        """
        for hard_copy in self.copies:
            try:
                copy_resolved = hard_copy.resolve(strict=True).joinpath(self.path.name)
            except FileNotFoundError:
                continue
            copy_absolute = hard_copy.joinpath(self.path.name)
            if copy_absolute.exists() and copy_absolute == copy_resolved:
                yield hard_copy

    def yield_unchanged_symlinks(self) -> Generator[pathlib.Path, None, None]:
        """Check each element in :attr:`.symlinnks` for on-disk changes.

        If the file no longer exists or no longer points to :attr:`.path`, we
        drop the reference to it.

        If we drop a reference, we log a warning.

        If the symlink is unchanged and valid, we yield it.
        """
        for symlink in self.symlinks:
            symlink_resolved = symlink.resolve().joinpath(self.path.name)
            symlink_absolute = symlink.absolute().joinpath(self.path.name)

            if symlink_absolute.exists() and symlink_resolved == self.path:
                yield symlink

    def update_file_references(self):
        """Update our reference lists of copies and symlinks of the managed file.

        If any of our references were converted from copies to symlinks or vice versa,
        we drop the reference.
        """

        self.copies = {copy for copy in self.yield_unchanged_copies()}

        self.symlinks = {symlink for symlink in self.yield_unchanged_symlinks()}

    def remove_from_dir(self, target_dir: pathlib.Path) -> bool:
        """Remove a copy or symlink of the managed file from the given `target_dir`.

        If the `target_dir` is not in one of :attr:`.copies` or :attr:`.symlinks`,
        this operation does nothing and returns `False`.

        If it i*is** present in one of them, we remove it from the set and call
        :meth:`pathlib.Path.unlink` on the path, if it exists. and return `True`.

        :raises NotADirectoryError: if `target_dir` isn't a directory.
        """
        if not target_dir.is_dir():
            raise NotADirectoryError(target_dir)

        if target_dir in self.copies:
            self.copies.remove(target_dir)
        elif target_dir in self.symlinks:
            self.symlinks.remove(target_dir)
        else:
            return False
        target = target_dir.joinpath(self.path.name)
        if target.exists():
            target.unlink()
        return True

    def copy_to_dir(self, target_dir: pathlib.Path, overwrite=False) -> pathlib.Path:
        """Create a copy of the managed file in the given `target_dir`.

        The copy created has the same file name as the string returned by :attr:`.path.name`.

        `target_dir` is added to :attr:`.copies` if a copy was created.

        If `target_dir` is listed already in :attr:`.symlinks`, we raise a
        :exc:`CannotImplicitlyChangeFileType` exception, even if `overwrite=True`
        was passed.

        If there already exists a copy and `overwrite` is `False`, we do nothing.
        Should `overwrite` be `True`, we overwrite the existing copy.

        :raises NotADirectoryError: if `target_dir` isn't a directory.
        :raises CannotImplicitlyChangeFileType:
            if the `target_dir` is already listed in :attr:`.symlinks`, which
            would implicitly replace the symlink with a hard copy.
        """
        if not target_dir.is_dir():
            raise NotADirectoryError(target_dir)

        target = target_dir.resolve().joinpath(self.path.name)
        if target_dir not in self.copies or overwrite:
            shutil.copyfile(str(self.path.resolve()), str(target.resolve()))
            self.copies.add(target_dir)
        return target

    def create_symlink(self, target_dir: pathlib.Path, overwrite: bool=False) -> pathlib.Path:
        """Create a symlink to the managed file in the given `target_dir`.

        The symlink created has the same file name as the string returned by :attr:`.path.name`.

        `target_dir` is added to :attr:`.symlinks` if a symlink was created.

        If `target_dir` is listed already in :attr:`.copies`, we raise a
        :exc:`CannotImplicitlyChangeFileType` exception, even if `overwrite=True`
        was passed.

        If there already exists a symlink and `overwrite` is `False`, we do nothing.
        Should `overwrite` be `True`, we overwrite the existing copy.

        :raises NotADirectoryError: if `target_dir` isn't a directory.
        :raises CannotImplicitlyChangeFileType:
            if the `target_dir` is already listed in :attr:`.copies`, which
            would implicitly replace the hard-copy with a symlink.
        """
        if not target_dir.is_dir():
            raise NotADirectoryError(target_dir)
        target = target_dir.resolve().joinpath(self.path.name)
        if target_dir not in self.symlinks or overwrite:
            # Create a symlink at target.
            target.symlink_to(self.path)
        self.symlinks.add(target_dir)
        return target
