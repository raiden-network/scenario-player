import pathlib
import shutil

from typing import Iterable, Optional, Tuple

from scenario_player.exceptions import TargetPathMustBeDirectory, FileOperationError


def parse_version( bin_path: pathlib.Path) -> Tuple[str, str]:
    """Extract the Archive or Binary's version and architecture from it's file name."""


class ManagedFile:
    """Generic file management interface."""
    def __init__(self, path: pathlib.Path, existing_symlinks: Optional[Iterable]=None, existing_copies: Optional[Iterable]=None) -> None:
        self.path = path
        self.copies = existing_copies or set()
        self.symlinks = existing_symlinks or set()

    @property
    def exists_locally(self) -> bool:
        return self.path.exists()

    @property
    def has_local_copies(self) -> bool:
        return bool(self.copies)

    @property
    def has_symlinks(self) -> bool:
        return bool(self.symlinks)

    def update_file_references(self):
        self.copies = {
            copy for copy in self.copies
            if copy.resolve().joinpath(self.path.name).exists()
        }
        self.symlinks = {
            symlink for symlink in self.copies
            if symlink.resolve().joinpath(self.path.name).exists()
               and symlink.resolve().joinpath(self.path.name).is_symlink()
        }

    def remove_from_dir(self, target_dir: pathlib.Path):
        if not target_dir.is_dir():
            raise TargetPathMustBeDirectory(target_dir)

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

    def copy_to_dir(self, target_dir: pathlib.Path, overwrite=False):
        if not target_dir.is_dir():
            raise TargetPathMustBeDirectory(target_dir)

        if target_dir not in self.copies or overwrite:
            target = target_dir.resolve().joinpath(self.path.name)
            shutil.copyfile(str(self.path.resolve()), str(target.resolve()))
            if not target.exists():
                raise FileOperationError(f'{str(target.resolve())} was copied but no longer exists!')
            self.copies.add(target_dir)

    def create_symlink(self, target_dir: pathlib.Path, overwrite: bool=False):
        if not target_dir.is_dir():
            raise TargetPathMustBeDirectory(target_dir)
        target = target_dir.resolve().joinpath(self.path.name)
        if not target.exists() or overwrite:
            # Create a symlink at target.
            target.symlink_to(self.path)


class RaidenBinary:
    """Wrapper class allowing simple management of a Raiden binary.

    Handles installation of the binary via :meth:`.install`

    Installs a binary from a RaidenArchive to a target directory, and keeps track
    of its existence.

    Installation may either happen as a symlink (default), or a full copy of
    the binary.

    The method may be called multiple times, with differing paths. Each invocation
    stores the passed `install_dir` in :attr:`install_dirs`.

    Handles unlinking installed binaries via :meth:`.uninstall`.

    Uninstalling removes the binary from the directory it was installed
    to using :meth:`.install`

    Allows removing an uninstalled binary from disk using :meth:`remove`.

    Removing a file only works if the property :attr:`.installed` is False.

    Uninstalling and removing may be run in a single command using :meth:`purge`.

    ..Note::

        You can only uninstall, remove or purge binaries via a path, if it was
        installed using this class interface. Manually installing a binary and
        calling :meth:`.uninstall` (or any other method removing a file from the system)
        will raise a :exc:`BinaryNotInstalled` exception or sub-class thereof.
    """

    def __init__(self, bin_path: pathlib.Path, install_dir: pathlib.Path=None):
        self.bin_path = bin_path
        self.install_dirs = {install_dir}
        self.version, self.arch = parse_version(bin_path)

    @property
    def installed(self):
        return len(self.install_dirs) == 0

    @property
    def exists_locally(self):
        return self.bin_path.exists()

    def install(self, install_dir: pathlib.Path, as_symlink: bool=True, overwrite: bool=False) -> pathlib.Path:
        """Install this binary to the given `install_dir`.

        By default, this is done by creating a symlink to :attr:`.bin_path` in
        `install_dir`.

        If you would like to make a copy of the binary at `install_dir` instead,
        pass `as_symlink=False`.

        If `install_dir` already exists in :attr:`.install_dirs`, installation
        is skipped, unless `overwrite` is True.
        """

    def uninstall(self, install_dir: Optional[pathlib.Path]=None):
        """Remove the symlink or copy of this binary from `install_dir`.

        If no `install_dir` is given, we remove all installed binaries.

        :param install_dir:
        :raises BinaryNotInstalledInDirectory:
            if the given `install_dir` is not present in :attr:`.install_dirs`.
        :raises BinaryNotInstalled: if :attr:`.install_dirs` is empty.
        """


class RaidenArchive:
    """Thin Wrapper class used to unpack archive files downloaded from the raiden cloud storage.

    Automatically detects the archive file type, and chooses a correct open function.

    Supports being used as a context manager, and validates archive file layout.
    """

    def __init__(self, path: pathlib.Path, unpacked_to: pathlib.Path=None):
        self.path = path
        self.unpacked_to = unpacked_to
        self.version = parse_version(bin_path)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def unpack(self, target_path: pathlib.Path) -> RaidenBinary:
        """Unpack this archive to the given `target_path`.

        The resulting binary will be used to create a :cls:`RaidenBinary`
        instance.
        """


def download_archive(version: str, cached: bool=True) -> RaidenArchive:
    """Download the archive for the given `version`."

    :param version: The version of Raiden to download the binary archive for.
    :param cached:
        Whether or not to use a cached archive, if any available. Defaults to `True`.
    """
