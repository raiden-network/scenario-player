import pathlib

from os import PathLike
from typing import Callable, List, Optional, Union

from scenario_player.utils.files.base import ManagedFile
from scenario_player.utils.files.constants import ARCHIVE_FNAME_TEMPLATE, CLOUD_STORAGE_URL
from scenario_player.utils.files.mixins import RaidenReleaseLikeMixin


class RaidenArchive(ManagedFile, RaidenReleaseLikeMixin):
    """Thin Wrapper class used to unpack archive files downloaded from the raiden cloud storage.

    Automatically detects the archive file type, and chooses a correct open function.

    Supports being used as a context manager, and validates archive file layout.
    """

    def __init__(self, path: PathLike, **kwargs):
        super(RaidenArchive, self).__init__(path, **kwargs)
        self._open: Union[Callable, None] = None
        self._list: Union[Callable, None] = None
        self._extract: Union[Callable, None] = None

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def detect_compression(self) -> None:
        """Detect the algorithm used to pack and/or compress the archive.

        :raises InvalidArchiveType:
            if we cannot figure out the algorithm used to compress the archive.
        """

    def validate_archive(self) -> None:
        """Ensure the archive has a valid structure.

        :raises InvalidArchiveLayout:
            if the archive does not contain exactly one file.
        """

    def open(self) -> None:
        """Open the file at :attr:`.path` in read-only mode.

        This calls the method stored at :attr:`._open` under the hood. If the
        attribute is `None`, we call :meth:`.detect_compression` first.
        """

    def list(self) -> List[pathlib.Path]:
        """Return the file or list of files in the archive.

        This calls the method stored at :attr:`._list` under the hood. If the
        attribute is `None`, we call :meth:`.detect_compression` first.
        """

    def extract(self, path: pathlib.Path) -> pathlib.Path:
        """Extract the archive to the given `path`.

        This calls the method stored at :attr:`._extract` under the hood.  If the
        attribute is `None`, we call :meth:`.detect_compression` first.

        From the method's return value we construct a :cls:`pathlib.Path` object
        pointing to the extracted file's location on the disk.
        """

    def unpack(self, target_path: Optional[PathLike]=None) -> PathLike:
        """Unpack this archive to the given `target_path`.

        If `target_path` is `None`, we default to `$HOME/.raiden/scenario-player/binaries`
        """


def construct_archive_fname(version: str) -> str:
    """Construct the archive file name from the current's systems information.

    Looks up the current machine's platform and architecture, and chooses an
    appropriate archive type (i.e. `zip`, `tar.gz` etc.).

    The platform is looked up using :var:`sys.platform`.

    The architecture is looked up using :func:`os.uname`, specifically the
    `machine` entry (index `4` of the returned tuple).

    These values, in addition to the given `version` are then injected into
    :var:`ARCHIVE_FNAME_TEMPLATE`, using :meth:`str.format`.

    the resulting string is returned.
    """


def download_archive(version: str, cached: bool=True) -> RaidenArchive:
    """Download the archive for the given `version`."

    `cached=True` (the default), will cause this method to first check if the
    file exists on the local machine (i.e. if it was already downloaded). Passing
    `cached=False` will force the method to download the archive again, regardless.

    The url to download is constructed by concatenating the result of
    :func:`construct_archive_fname` and :var:`.CLOUD_STORAGE_URL`.

    :param version: The version of Raiden to download the binary archive for.
    :param cached:
        Whether or not to use a cached archive, if any available. Defaults to `True`.
    """
