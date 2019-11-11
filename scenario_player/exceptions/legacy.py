class ScenarioError(Exception):
    exit_code = 20


class ScenarioTxError(ScenarioError):
    exit_code = 21


class TokenRegistrationError(ScenarioTxError):
    exit_code = 22


class TokenNetworkDiscoveryTimeout(TokenRegistrationError):
    """If we waited a set time for the token network to be discovered, but it wasn't."""

    exit_code = 22


class ChannelError(ScenarioError):
    exit_code = 23


class TransferFailed(ScenarioError):
    exit_code = 24


class NodesUnreachableError(ScenarioError):
    exit_code = 25


class RESTAPIError(ScenarioError):
    exit_code = 26


class RESTAPIStatusMismatchError(ScenarioError):
    exit_code = 26


class RESTAPITimeout(RESTAPIError):
    exit_code = 26


class MultipleTaskDefinitions(ScenarioError):
    """Several root tasks were defined in the scenario configuration."""

    exit_code = 27


class InvalidScenarioVersion(ScenarioError):
    exit_code = 27


class UnknownTaskTypeError(ScenarioError):
    exit_code = 27


class MissingNodesConfiguration(ScenarioError, KeyError):
    """Could not find a key in the scenario file's 'nodes' section."""

    exit_code = 28


class ScenarioAssertionError(ScenarioError):
    exit_code = 30


class BrokenArchive(Exception):
    """There was an error opening the archive and it is likely corrupted."""


class ArchiveNotAvailableOnLocalMachine(FileNotFoundError):
    """The archive was not found on the local machine."""


class InvalidArchiveLayout(ValueError):
    """The archive did contain the expected folder structure."""


class InvalidArchiveType(TypeError):
    """The archive file is not a zip or tar gz file."""


class InvalidReleaseVersion(ValueError):
    """The given version does not exist or could not be found in the raiden cloud."""


class TargetPathMustBeDirectory(TypeError):
    """A pathlib.Path object was passed that is not a directory."""


class FileOperationError(OSError):
    """We copied a file but the created copy was not found.

    This is error is raised when we believe there may be a race condition causing
    our file to disappear.
    """
