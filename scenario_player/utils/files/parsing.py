import os


from typing import Tuple


def parse_version(path: os.PathLike) -> str:
    """Extract the Archive or Binary's version from it's file name.

    If no version can be parsed, return `None`.
    """


def parse_architecture(path: os.PathLike) -> str:
    """Extract the Archive or Binary's architecture from it's file name.

    If no architecture can be parsed, return `None`.
    """


def parse_platform(path: os.PathLike) -> str:
    """Extract the Archive or Binary's platform from it's file name.

    If no platform can be parsed, return `None`.
    """


def detect_target_config(path: os.PathLike) -> Tuple[str, str, str]:
    """Parse the version, architecture and platform from the given  `path`."""
    return parse_version(path), parse_platform(path), parse_architecture(path)
