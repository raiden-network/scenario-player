import json

import pytest


@pytest.fixture
def expected_defaults():
    """A dict containing all expected default values for keys of any ConfigMapping."""
    return {
        "version": 2,
        "name": "<Unnamed Scenario>",
        "scenario": {"serial": {"runner": None, "config": "salami"}},
        "settings": {
            "gas_price": "fast",
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
    }


@pytest.fixture
def minimal_yaml_dict():
    """A dictionary with the minimum required keys for instantiating any ConfigMapping."""
    return {
        "scenario": {"serial": {"runner": None, "config": "salami"}},
        "settings": {},
        "token": {},
        "nodes": {"count": 1},
    }


@pytest.fixture
def token_info_path(tmp_path):
    path = tmp_path.joinpath("token.info")
    path.touch()
    with path.open("w") as f:
        json.dump({"token_name": "my_token", "address": "my_address", "block": 0}, f)
    return path
