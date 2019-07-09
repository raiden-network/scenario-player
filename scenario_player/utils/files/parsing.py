import os
import pathlib
import re
from typing import Tuple, Union




def match_pattern_in_path(pattern, path, key) -> Union[str, None]:
    compiled = re.compile(pattern)
    match = compiled.match(pathlib.Path(path).name)
    if match:
        return match.groupdict().get(key)
    return None


def parse_version(path: os.PathLike) -> Union[str, None]:
    """Extract the Archive or Binary's version from it's file name.

    If no version can be parsed, return `None`.
    """
    return match_pattern_in_path(VERSION_REGEX, path, "version")


def parse_architecture(path: os.PathLike) -> Union[str, None]:
    """Extract the Archive or Binary's architecture from it's file name.

    If no architecture can be parsed, return `None`.
    """
    return match_pattern_in_path(ARCH_REGEX, path, "architecture")


def parse_platform(path: os.PathLike) -> Union[str, None]:
    """Extract the Archive or Binary's platform from it's file name.

    If no platform can be parsed, return `None`.
    """
    return match_pattern_in_path(PLATFORM_REGEX, path, "platform")


def detect_target_config(path: os.PathLike) -> Tuple[Union[str, None], Union[str, None], Union[str, None]]:
    """Parse the version, architecture and platform from the given  `path`."""
    return parse_version(path), parse_platform(path), parse_architecture(path)
