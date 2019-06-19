import pathlib

from os import PathLike
from typing import Optional

from scenario_player.exceptions.files import BinaryNotInstalled, BinaryNotInstalledInDirectory
from scenario_player.utils.files.base import ManagedFile
from scenario_player.utils.files.mixins import RaidenReleaseLikeMixin


class RaidenBinary(ManagedFile, RaidenReleaseLikeMixin):
    """Wrapper class allowing simple management of a Raiden binary.

    Handles installation of the binary via :meth:`.install`

    The default installation directory is `$HOME/.raiden/scenario-player/binaries`.

    Installs a binary to a target directory, and keeps track
    of its existence.

    Installation may either happen as a symlink (default), or a full copy of
    the binary.

    The method may be called multiple times, with differing paths. Each invocation
    stores the passed `install_dir` in :attr:`install_dirs`.

    Handles unlinking installed binaries via :meth:`.uninstall`.

    Uninstalling removes the binary from the directory it was installed
    to using :meth:`.install`.

    Uninstalling and removing may be run in a single command using :meth:`purge`.

    ..Note::

        You can only uninstall, remove or purge binaries, if they were installed
        using this class interface. Manually installing a binary and
        calling :meth:`.uninstall` or :meth:`.purge` will raise a
        :exc:`BinaryNotInstalled` exception or sub-class thereof.
    """

    @property
    def install_dirs(self):
        return self.copies & self.symlinks

    @property
    def installed(self) -> bool:
        """Whether or not there were installations made using this class."""

    @property
    def is_executable(self) -> bool:
        """Whether or not the `x` bit is set on the managed binary files."""

    def install(self, install_dir: Optional[PathLike]=None, as_symlink: bool=True, overwrite: bool=False) -> pathlib.Path:
        """Install this binary to `install_dirs`.

        If `install_dir` is `None`, we default to `$HOME//scenario-player/binaries`.

        By default, installation is done by creating a symlink to :attr:`.path` in
        `install_dir`.

        If you would like to make a copy of the binary at `install_dir` instead,
        pass `as_symlink=False`.

        The parameters `install_dir` and `overwrite` are passed on to other
        instance methods inherited from :cls:`ManagedFile` depending on the value
        of `as_symlink`; these being :meth:`.create_symlink`, :meth:`.copy_to_dir`.
        """

    def uninstall(self, install_dir: Optional[PathLike]=None) -> None:
        """Remove the symlink or copy of this binary from `install_dir`.

        If no `install_dir` is given, we remove all installed binaries.

        :raises BinaryNotInstalledInDirectory:
            if the given `install_dir` is not present in :attr:`.install_dirs`.
        :raises BinaryNotInstalled: if :attr:`.install_dirs` is empty.
        """
        # FIXME: This is a stub.
        try:
            if install_dir:
                raise BinaryNotInstalledInDirectory
            else:
                raise BinaryNotInstalled
        except FileNotFoundError:
            pass