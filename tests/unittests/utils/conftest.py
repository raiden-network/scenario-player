import json

import pytest


@pytest.fixture
def minimal_yaml_dict():
    """A dictionary with the minimum required keys for instantiating any ConfigMapping."""
    return {
        "scenario": {"serial": {"runner": None, "config": "salami"}},
        "settings": {},
        "token": {},
        "nodes": {"count": 1},
        "spaas": {},
    }


@pytest.fixture
def token_info_path(tmp_path):
    path = tmp_path.joinpath("token.info")
    path.touch()
    with path.open("w") as f:
        json.dump({"token_name": "my_token", "address": "my_address", "block": 0}, f)
    return path
