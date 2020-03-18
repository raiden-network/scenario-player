import datetime
import json
import pathlib
import uuid

import structlog

from scenario_player.constants import DEFAULT_TOKEN_BALANCE_FUND, DEFAULT_TOKEN_BALANCE_MIN
from scenario_player.exceptions.config import TokenConfigurationError

log = structlog.get_logger(__name__)


class TokenConfig:
    """Configuration for the token to be used in the scenario.

    Example scenario definition section::

        >my_scenario.yaml
        version: 2
        ...
        token:
          token_name: MySuperToken
          address: "x0100001"
          symbol: SPRTKN
          decimals: 2
          balance_min: 400
          balance_fund: 400
        ...

    ..note::

        When setting the option `reuse` in the definition file, it is an error
        to also give an `address` option - these two options are mutually exclusive!
    """

    CONFIGURATION_ERROR = TokenConfigurationError

    def __init__(self, loaded_definition: dict, token_info_fpath: pathlib.Path):
        self.dict = loaded_definition.get("token", {})
        self._token_id = uuid.uuid4()
        self._name = None
        self._token_file = token_info_fpath
        self.validate()

    def validate(self):
        """Validate the configuration section.

        Asserts that:

            * Mutually exclusive options are not truthy
        """
        mutual_exclusive_ops = ("address", "reuse")

        if all(option in self.dict for option in mutual_exclusive_ops):
            assert (
                bool(self.dict["address"]) != self.dict["reuse"]
            ), f"Token settings {mutual_exclusive_ops} are mutually exclusive."

        if self.token_info:
            keys = ("token_name", "address", "block")
            assert all(
                k in self.token_info for k in keys
            ), f"token.info file missing one or more of expected keys: {keys}"

    @property
    def token_info(self):
        if self._token_file.exists():
            return json.loads(self._token_file.read_text())
        return None

    @property
    def name(self):
        """Return the token's name.

        If reuse is True, this will fetch the 'token_name' key from any loaded
        token data from the token.info file, if such a key is available. Falls
        back to None if the key isn't present.
        """
        if self.reuse_token:
            return self.token_info.get("token_name")

        if not self._name:
            now = datetime.datetime.now()
            self._name = self.dict.get(
                "name", f"Scenario Test Token {self._token_id!s} {now:%Y-%m-%dT%H:%M}"
            )
        return self._name

    @property
    def address(self):
        return self.dict.get("address")

    @property
    def reuse_token(self):
        return self.dict.get("reuse", False) and self._token_file.exists()

    @property
    def symbol(self):
        return self.dict.get("symbol", f"T{self._token_id!s:.3}")

    @property
    def decimals(self):
        return self.dict.get("decimals", 0)

    @property
    def min_balance(self):
        """The required minimum balance required for the scenario run."""
        return self.dict.get("balance_min", DEFAULT_TOKEN_BALANCE_MIN)

    @property
    def max_funding(self):
        """The maximum amount we fund an account with."""
        return self.dict.get("balance_fund", DEFAULT_TOKEN_BALANCE_FUND)
