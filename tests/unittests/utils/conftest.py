import json

import pytest

from ..conftest import dummy_scenario_runner, minimal_yaml_dict


@pytest.fixture
def token_info_path(tmp_path):
    path = tmp_path.joinpath("token.info")
    path.touch()
    with path.open("w") as f:
        json.dump({"token_name": "my_token", "address": "my_address", "block": 0}, f)
    return path
