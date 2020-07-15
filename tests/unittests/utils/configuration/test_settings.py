import pytest
from eth_typing import URI
from web3.gas_strategies.time_based import fast_gas_price_strategy, medium_gas_price_strategy

from raiden.utils.typing import BlockTimeout, FeeAmount, TokenAddress, TokenAmount
from scenario_player.utils.configuration.settings import (
    EnvironmentConfig,
    PFSSettingsConfig,
    ServiceSettingsConfig,
    SettingsConfig,
    UDCSettingsConfig,
    UDCTokenSettings,
)

dummy_env = EnvironmentConfig(
    pfs_fee=FeeAmount(100),
    environment_file_name="tests",
    environment_type="development",
    matrix_servers=[],
    transfer_token=TokenAddress(bytes([1] * 20)),
    pfs_with_fee=URI("http://www.example.com"),
    eth_rpc_endpoints=[URI("http://www.example.com")],
    ms_reward_with_margin=TokenAmount(1),
    settlement_timeout_min=BlockTimeout(100),
)


class TestSettingsConfig:
    @pytest.mark.parametrize("key", ["timeout", "gas_price"])
    def test_class_returns_expected_default_for_key(
        self, key, expected_defaults, minimal_definition_dict
    ):
        """If supported  keys are absent, sensible defaults are returned for them when accessing
        them as a class attribute."""
        config = SettingsConfig(minimal_definition_dict, dummy_env)

        try:
            actual = getattr(config, key)
        except AttributeError as e:
            raise AssertionError(e)

        assert expected_defaults["settings"][key] == actual

    def test_settings_attr_returns_service_settings_config_instance(self, minimal_definition_dict):
        config = SettingsConfig(minimal_definition_dict, dummy_env)
        assert isinstance(config.services, ServiceSettingsConfig)

    @pytest.mark.parametrize(
        "value, raises",
        argvalues=[("super-fast", True), (11, False), ("fast", False)],
        ids=["Unknown strategy key", "valid integer value", "Valid strategy ket"],
    )
    def test_validate_raises_exception_for_invalid_gas_price_values(
        self, value, raises, minimal_definition_dict
    ):
        minimal_definition_dict["settings"]["gas_price"] = value
        try:
            SettingsConfig(minimal_definition_dict, dummy_env)
        except Exception:
            if not raises:
                pytest.fail("Raised ScenarioConfigurationError unexpectedly!")

    def test_gas_price_strategy_returns_a_callable(self, minimal_definition_dict):
        """The :attr:`SettingsConfig.gas_price_strategy` returns a callable."""
        config = SettingsConfig(minimal_definition_dict, dummy_env)
        assert callable(config.gas_price_strategy)

    @pytest.mark.parametrize(
        "strategy, expected_func",
        argvalues=[("fast", fast_gas_price_strategy), ("medium", medium_gas_price_strategy)],
    )
    def test_gas_price_strategy_property_returns_strategy_from_web3(
        self, strategy, expected_func, minimal_definition_dict
    ):
        """The gas price strategy is dynamically fetched."""
        minimal_definition_dict["settings"]["gas_price"] = strategy
        config = SettingsConfig(minimal_definition_dict, dummy_env)
        assert config.gas_price_strategy == expected_func


class TestServiceSettingsConfig:
    def test_pfs_attribute_returns_pfs_settings_config(self, minimal_definition_dict):
        config = ServiceSettingsConfig(minimal_definition_dict, dummy_env)
        assert isinstance(config.pfs, PFSSettingsConfig)

    def test_ucd_attribute_returns_udc_settings_config(self, minimal_definition_dict):
        config = ServiceSettingsConfig(minimal_definition_dict, dummy_env)
        assert isinstance(config.udc, UDCSettingsConfig)


class TestPFSSettingsConfig:
    def test_url_attribute_returns_default_none_if_key_absent(self, minimal_definition_dict):
        config = PFSSettingsConfig(minimal_definition_dict)
        assert config.url is None

    def test_url_attribute_returns_url_key_value_if_key_present(self, minimal_definition_dict):
        minimal_definition_dict["settings"]["services"] = {"pfs": {"url": "custom_url"}}
        config = PFSSettingsConfig(minimal_definition_dict)
        assert config.url == "custom_url"


class TestUDCSettingsConfig:
    def test_token_attribute_is_an_instance_of_udctokenconfig(self, minimal_definition_dict):
        assert isinstance(
            UDCSettingsConfig(minimal_definition_dict, dummy_env).token, UDCTokenSettings
        )

    @pytest.mark.parametrize("key, expected", argvalues=[("enable", False), ("address", None)])
    def test_attributes_whose_key_is_absent_return_expected_default(
        self, key, expected, minimal_definition_dict
    ):
        config = UDCSettingsConfig(minimal_definition_dict, dummy_env)
        MISSING = object()
        assert getattr(config, key, MISSING) == expected

    @pytest.mark.parametrize("key, expected", argvalues=[("enable", True), ("address", "walahoo")])
    def test_attributes_return_for_key_value_if_key_present(
        self, key, expected, minimal_definition_dict
    ):
        minimal_definition_dict["settings"] = {"services": {"udc": {key: expected}}}
        config = UDCSettingsConfig(minimal_definition_dict, dummy_env)
        MISSING = object()
        assert getattr(config, key, MISSING) == expected


class TestUDCTokenConfig:
    @pytest.mark.parametrize(
        "key, expected",
        argvalues=[("deposit", False), ("balance_per_node", 1000), ("max_funding", 10_000)],
    )
    def test_attributes_return_for_key_value_if_key_present(
        self, key, expected, minimal_definition_dict
    ):
        minimal_definition_dict["settings"] = {"services": {"udc": {"token": {key: expected}}}}
        config = UDCTokenSettings(minimal_definition_dict, dummy_env)
        MISSING = object()
        assert getattr(config, key, MISSING) == expected

    @pytest.mark.parametrize(
        "key, expected",
        argvalues=[("deposit", True), ("balance_per_node", 5000), ("max_funding", 5000)],
    )
    def test_attributes_whose_key_is_absent_return_expected_default(
        self, key, expected, minimal_definition_dict
    ):
        config = UDCTokenSettings(minimal_definition_dict, dummy_env)
        MISSING = object()
        assert getattr(config, key, MISSING) == expected

    def test_balance_per_node_must_not_be_greater_than_max_funding(self, minimal_definition_dict):
        minimal_definition_dict["settings"] = {
            "services": {"udc": {"token": {"max_funding": 6000, "balance_per_node": 6001}}}
        }
        with pytest.raises(Exception):
            UDCTokenSettings(minimal_definition_dict, dummy_env)
