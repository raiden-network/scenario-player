import pytest

from scenario_player.utils.configuration.spaas import SPaaSConfig, SPaaSServiceConfig


@pytest.mark.parametrize(
    "prop, expected_value",
    argvalues=[("scheme", "http"), ("port", "5000"), ("netloc", "localhost:5000")],
)
def test_service_config_properties_return_expected_defaults_if_keys_missing(prop, expected_value):
    service_config = SPaaSServiceConfig({})
    assert getattr(service_config, prop) == expected_value


@pytest.mark.parametrize(
    "prop, expected_value",
    argvalues=[("scheme", "bobbity"), ("port", "1"), ("netloc", "schmooby.com:1")],
)
def test_service_config_properties_return_values_of_keys_if_key_present(prop, expected_value):
    conf = {"scheme": "bobbity", "host": "schmooby.com", "port": "1"}
    service_config = SPaaSServiceConfig(conf)

    assert getattr(service_config, prop) == expected_value


@pytest.mark.parametrize("attr", argvalues=["rpc"])
def test_spaas_config_returns_spaas_service_config_when_accessig_service_configs_via_attribute(
    attr
):
    assert isinstance(getattr(SPaaSConfig({}), attr), SPaaSServiceConfig)


def test_spaas_config_inits_rpc_service_config_with_correct_dict():
    expected_service_conf = {"scheme": "bobbity", "host": "schmooby.com", "port": "1"}
    conf = SPaaSConfig({"spaas": {"rpc": expected_service_conf}})
    assert conf.rpc == expected_service_conf
