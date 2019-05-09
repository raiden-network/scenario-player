
class RaidenArchive:

    def __init__(self, archive_path: pathlib.Path):
        self.path = archive_path

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def unpack(self, target_path: pathlib.Path) -> pathlib.Path:
        pass


def download_archive(version: str) -> RaidenArchive:
    """Download the archive for the given `version`."""
