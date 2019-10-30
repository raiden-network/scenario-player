from raiden_contracts.constants import CONTRACTS_VERSION

from raiden.utils import get_system_spec as raiden_system_spec
from scenario_player import __version__


def get_complete_spec():
    """Gather raiden system specification and add scenario player information."""
    spec = raiden_system_spec()
    spec["scenario_player"] = __version__
    spec["raiden-contracts"] = CONTRACTS_VERSION
    return spec
