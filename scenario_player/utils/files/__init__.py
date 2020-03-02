from scenario_player.utils.files.base import ManagedFile
from scenario_player.utils.files.constants import (
    ARCHIVE_FNAME_TEMPLATE,
    BINARY_FNAME_TEMPLATE,
    CLOUD_STORAGE_URL,
)
from scenario_player.utils.files.parsing import (
    detect_target_config,
    parse_architecture,
    parse_platform,
    parse_version,
)

__all__ = [
    "ManagedFile",
    "ARCHIVE_FNAME_TEMPLATE",
    "BINARY_FNAME_TEMPLATE",
    "CLOUD_STORAGE_URL",
    "parse_version",
    "parse_platform",
    "parse_architecture",
    "detect_target_config",
]
