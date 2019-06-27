from scenario_player.utils.files.base import ManagedFile
from scenario_player.utils.files.constants import (
    ARCHIVE_FNAME_TEMPLATE,
    BINARY_FNAME_TEMPLATE,
    CLOUD_STORAGE_URL,
)
from scenario_player.utils.files.mixins import (
    ArchitectureSpecificMixin,
    VersionedMixin,
    PlatformSpecificMixin,
)
from scenario_player.utils.files.parsing import (
    parse_version,
    parse_architecture,
    parse_platform,
    detect_target_config,
)
