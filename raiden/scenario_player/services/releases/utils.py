
class RaidenArchive:
    """Thin Wrapper class used to unpack archive files downloaded from the raiden cloud storage.

    Automatically detects the archive file type, and chooses a correct open function.

    Supports being used as a context manager, and validates archive file layout.
    """

    def __init__(self, archive_path: pathlib.Path):
        self.path = archive_path

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def unpack(self, target_path: pathlib.Path) -> pathlib.Path:
        pass


def download_archive(version: str, cached: bool=True) -> RaidenArchive:
    """Download the archive for the given `version`."

    :param version: The version of Raiden to download the binary archive for.
    :param cached:
        Whether or not to use a cached archive, if any available. Defaults to `True`
    """
