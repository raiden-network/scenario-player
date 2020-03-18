import pytest


@pytest.fixture
def expected_defaults():
    """A dict containing all expected default values for keys of any config."""
    return {
        "version": 2,
        "name": "<Unnamed Scenario>",
        "scenario": {"serial": {"runner": None, "config": "salami"}},
        "settings": {
            "gas_price": "FAST",
            "timeout": 200,
            "notify": None,
            "chain": "goerli",
            "services": {},
        },
        "token": {"address": None, "block": 0, "reuse": False, "symbol": str(), "decimals": 0},
        "nodes": {
            "count": 1,
            "commands": {},
            "default_options": {},
            "node_options": {},
            "raiden_version": "LATEST",
        },
    }
