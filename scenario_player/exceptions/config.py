class ConfigurationError(ValueError):
    """Generic error thrown if there was an error while reading the scenario file."""


class NodeConfigurationError(ConfigurationError):
    """An error occurred while validating the nodes setting of a scenario file."""


class ScenarioConfigurationError(ConfigurationError):
    """An error occurred while validating the scenario setting of a scenario file."""


class TokenConfigurationError(ConfigurationError):
    """There was a problem while setting up the token contract.

    This may include exceptions which occurred duing file parsing, or during
    contract creation.
    """


class TokenSourceCodeDoesNotExist(TokenConfigurationError):
    """The requested address does not contain source code."""


class TokenFileError(ConfigurationError):
    """There was an error while reading a token configuration from disk."""


class TokenSaveError(TokenFileError):
    """Could not safe the token file, likely because of missing permissions or missing values."""


class TokenFileMissing(TokenFileError):
    """We tried re-using a token, but no token.info file exists for it."""


class ServiceConfigurationError(ConfigurationError):
    """There was a problem validating the services configuration setting."""
