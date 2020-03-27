import json
import pathlib

import pytest

from scenario_player.definition import ScenarioDefinition


@pytest.mark.parametrize(
    "token,default_options,environment_type",
    [
        (dict(), None, "development"),
        (dict(), dict(), "development"),
        (dict(address=""), dict(), None),
        (dict(address=""), {"environment-type": "production"}, "production"),
        (dict(), {"environment-type": "production"}, "production"),
    ],
    ids=[
        "deal_with_None",
        "default_environment_type",
        "no_change",
        "standard_behavior",
        "respect_override",
    ],
)
def test_environment_default_type_on_token(tmpdir, token, default_options, environment_type):
    dir = tmpdir.mkdtemp()
    testfile = dir.join("test.yaml")
    with open(testfile, "w") as f:
        data = dict(
            version=2,
            settings=dict(),
            token=token,
            nodes=dict(count=1, default_options=default_options)
            if default_options is not None
            else dict(count=1),
            scenario=dict(serial=dict()),
        )
        json.dump(data, f)
    definition = ScenarioDefinition(
        yaml_path=pathlib.Path(testfile), data_path=pathlib.Path(dir), environment={}
    )
    if environment_type is not None:
        assert definition.nodes.default_options["environment-type"] == environment_type
    else:
        assert "environment-type" not in definition.nodes.default_options
