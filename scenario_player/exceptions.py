class ScenarioError(Exception):
    pass


class ScenarioTxError(ScenarioError):
    pass


class TokenRegistrationError(ScenarioTxError):
    pass


class ChannelError(ScenarioError):
    pass


class TransferFailed(ScenarioError):
    pass


class NodesUnreachableError(ScenarioError):
    pass


class RESTAPIError(ScenarioError):
    pass


class RESTAPIStatusMismatchError(ScenarioError):
    pass


class RESTAPITimeout(RESTAPIError):
    pass


class MultipleTaskDefinitions(ScenarioError):
    """Several root tasks were defined in the scenario configuration."""


class InvalidScenarioVersion(ScenarioError):
    pass


class UnknownTaskTypeError(ScenarioError):
    pass


class MissingNodesConfiguration(ScenarioError, KeyError):
    """Could not find a key in the scenario file's 'nodes' section."""


class ScenarioAssertionError(ScenarioError):
    pass


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
