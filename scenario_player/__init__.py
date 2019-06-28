"""Raiden Scenario Player.

End-to-end testing tool for the ``Raiden`` test suite.
"""
from scenario_player.services.common.plugins import (
    register_hook_implementations, register_hook_specifications, HOST_NAMESPACE
)

__version__ = "0.1.0"


# Register the core hook specs and their implementations from our library.
register_hook_specifications(HOST_NAMESPACE)
register_hook_implementations(HOST_NAMESPACE)
