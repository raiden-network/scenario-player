class ScenarioError(Exception):
    pass


class ScenarioTxError(ScenarioError):
    pass


class TokenRegistrationError(ScenarioTxError):
    pass


class TransferFailed(ScenarioError):
    pass


class RESTAPIError(ScenarioError):
    pass


class RESTAPIStatusMismatchError(ScenarioError):
    pass


class RESTAPITimeout(RESTAPIError):
    pass


class UnknownTaskTypeError(ScenarioError):
    pass


class ScenarioAssertionError(ScenarioError):
    pass
