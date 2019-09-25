from scenario_player.exceptions.config import ConfigurationError


class ArchiveNotFound(ConfigurationError):
    """We tried downloading an archive, which does not exist - check your raiden version!"""
