from scenario_player.exceptions.config import ConfigurationError


class ArchiveNotFound(ConfigurationError):
    """We tried downloading an archive, which does not exist - check your raiden version!"""


class NotInstalled(ConfigurationError):
    """`raiden_version: local` was set in the scenario definition, but we found no valid
    executable in the current environment."""
