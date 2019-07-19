from collections.abc import Mapping
from typing import Optional, Union

import structlog

from scenario_player.exceptions.config import ConfigurationError

log = structlog.get_logger(__name__)


class ConfigMapping(Mapping):
    def __init__(self, loaded_yaml: Mapping):
        self.dict = loaded_yaml

    def __getitem__(self, item):
        return self.dict[item]

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    @staticmethod
    def assert_option(expression, err: Optional[Union[str, Exception]] = None):
        """Wrap `assert` to raise a ConfigurationError instead of an AssertionError."""
        try:
            assert expression
        except AssertionError as e:
            if err is None or isinstance(err, str):
                raise ConfigurationError(err)
            else:
                exception = err
            raise exception from e

    def validate(self):
        """Validate the configuration.

        Assert that all required keys are present, and no mutually exclusive
        options were set.
        """
