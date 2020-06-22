class ScenarioError(Exception):
    exit_code = 20


class ScenarioTxError(ScenarioError):
    exit_code = 21


class TokenRegistrationError(ScenarioTxError):
    exit_code = 22


class TokenNetworkDiscoveryTimeout(TokenRegistrationError):
    """If we waited a set time for the token network to be discovered, but it wasn't."""

    exit_code = 22


class TransferFailed(ScenarioError):
    exit_code = 24


class RESTAPIError(ScenarioError):
    exit_code = 26


class RESTAPIStatusMismatchError(ScenarioError):
    exit_code = 26


class RESTAPITimeout(RESTAPIError):
    exit_code = 26


class UnknownTaskTypeError(ScenarioError):
    exit_code = 27


class ScenarioAssertionError(ScenarioError):
    exit_code = 30
