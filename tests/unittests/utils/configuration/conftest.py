import json

import pytest

from ..conftest import minimal_yaml_dict, token_info_path


@pytest.fixture
def expected_defaults():
    """A dict containing all expected default values for keys of any ConfigMapping."""
    return {
        "version": 2,
        "name": "<Unnamed Scenario>",
        "scenario": {"serial": {"runner": None, "config": "salami"}},
        "settings": {
            "gas_price": "FAST",
            "timeout": 200,
            "notify": None,
            "chain": "any",
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
        "spaas": {"rpc": {"scheme": "https", "host": "localhost", "port": 5100}},
    }
