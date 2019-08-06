from collections.abc import Mapping
from typing import Optional, Union

import structlog

from scenario_player.exceptions.config import ConfigurationError

log = structlog.get_logger(__name__)


class ConfigMapping(Mapping):

    CONFIGURATION_ERROR = ConfigurationError

    def __init__(self, loaded_yaml: Mapping):
        self.dict = loaded_yaml or {}

    def __getitem__(self, item):
        return self.dict[item]

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    def __eq__(self, other):
        if isinstance(other, dict):
            return self.dict == other
        elif isinstance(other, ConfigMapping):
            return self.dict == other.dict
        raise TypeError(f"Incomparable types! {self.__class__.__qualname__} and {type(other)}")

    def __str__(self):
        return str(self.dict)

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.dict})"

    @classmethod
    def assert_option(cls, expression, err: Optional[Union[str, Exception]] = None):
        """Wrap `assert` to raise a ConfigurationError instead of an AssertionError."""
        try:
            assert expression
        except AssertionError as e:
            if err is None or isinstance(err, str):
                raise cls.CONFIGURATION_ERROR(err) from e
            else:
                exception = err
            raise exception from e

    def validate(self):
        """Validate the configuration.

        Assert that all required keys are present, and no mutually exclusive
        options were set.
        """
