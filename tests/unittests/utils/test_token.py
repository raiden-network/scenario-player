import json
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from raiden_contracts.contract_manager import ContractManager
from requests.exceptions import (
    ConnectionError,
    ConnectTimeout,
    HTTPError,
    ProxyError,
    ReadTimeout,
    RequestException,
    RetryError,
    SSLError,
    Timeout,
)

from raiden.network.rpc.client import AddressWithoutCode, JSONRPCClient
from scenario_player.exceptions.config import (
    TokenFileError,
    TokenFileMissing,
    TokenNotDeployed,
    TokenSourceCodeDoesNotExist,
)
from scenario_player.utils.configuration.spaas import SPaaSConfig
from scenario_player.utils.configuration.token import TokenConfig
from scenario_player.utils.token import Token

token_import_path = "scenario_player.utils.token"
token_config_import_path = "scenario_player.utils.configuration.token"


class Sentinel(Exception):
    """Raised when it's desired to exit a method under test early."""


@pytest.fixture
def config(minimal_yaml_dict, token_info_path):
    """Returns a mock config with a minimal yaml config and tmp path without token.info file."""

    token_config = TokenConfig(minimal_yaml_dict, token_info_path)

    class MockConfig:
        def __init__(self):
            self.token = token_config
            self.spaas = SPaaSConfig(minimal_yaml_dict)

    yield MockConfig()


@pytest.fixture
def runner():
    class MockRunner:
        def __init__(self):
            self.client = MagicMock(spec=JSONRPCClient)
            self.contract_manager = MagicMock(spec=ContractManager)

    return MockRunner()


@pytest.fixture
def instance_under_test(config, runner, tmp_path):
    return Token(config, runner, tmp_path)


@pytest.mark.dependency(name="TestClass")
class TestToken:
    @patch(f"{token_import_path}.ServiceInterface")
    def test_constructor_loads_attributes_correctly(
        self, mock_interface, config, runner, tmp_path
    ):
        """The following attributes are loaded correctly from the given parameters:

            - :attr:`Token.interface` is an instance of :class:`ServiceInterface` and constructed
                using the passed `yaml_config` paramter.
            - :attr:`Token._local_rpc_client` is loaded from :attr:`runner.client`
            - :attr:`Token._local_contract_manager` is loaded from
                :attr:`runner.client.contract_manager`
            - :attr:`Token._token_file` is constructed by joining the `data_path`
                parameter with `token.info`.

        """
        iface = object()
        mock_interface.return_value = iface
        token = Token(config, runner, tmp_path)

        mock_interface.assert_called_once_with(config.spaas)
        assert token.interface == iface

        assert token._local_rpc_client == runner.client
        assert token._local_contract_manager == runner.contract_manager
        assert token._token_file == tmp_path.joinpath("token.info")
        assert token.config == config.token

    @pytest.mark.parametrize("prop", argvalues=["name", "symbol", "decimals"])
    @patch(f"{token_config_import_path}.TokenConfig.decimals", new_callable=PropertyMock)
    @patch(f"{token_config_import_path}.TokenConfig.symbol", new_callable=PropertyMock)
    @patch(f"{token_config_import_path}.TokenConfig.name", new_callable=PropertyMock)
    def test_properties__delegate_to_equivalent_property_on_token_config(
        self, m_name, m_symbol, m_decimals, prop, config, runner, tmp_path
    ):
        mocked_properties = {"name": m_name, "symbol": m_symbol, "decimals": m_decimals}
        token = Token(config, runner, tmp_path)
        getattr(token, prop)
        assert len(mocked_properties[prop].mock_calls) == 1

    @patch(f"{token_config_import_path}.TokenConfig.address", new_callable=PropertyMock)
    def test_address_is_fetched_from_contract_data_if_available(
        self, mock_address, config, runner, tmp_path
    ):
        token = Token(config, runner, tmp_path)
        token.contract_data = {"contract_address": 100}
        mock_address.return_value = 200
        assert token.address == 100

    @patch(f"{token_config_import_path}.TokenConfig.address", new_callable=PropertyMock)
    def test_address_is_fetched_from_token_config_if_no_contract_data_available(
        self, mock_address, config, runner, tmp_path
    ):
        token = Token(config, runner, tmp_path)
        mock_address.return_value = 100
        assert token.address == 100

    @patch(f"{token_import_path}.to_checksum_address")
    def test_checksum_address_property_address_in_token_config_if_token_is_not_deployed(
        self, mock_to_checksum, instance_under_test
    ):
        # inject address key to token config
        instance_under_test.config.dict["address"] = "my_addr"
        assert instance_under_test.contract_data == {}
        instance_under_test.checksum_address
        mock_to_checksum.assert_called_once_with("my_addr")

    @patch(f"{token_import_path}.to_checksum_address")
    def test_checksum_address_returns_checksummed_raw_address_from_contract_data_if_available(
        self, mock_checksum, config, runner, tmp_path
    ):
        token = Token(config, runner, tmp_path)

        raw_addr = "0x12ae66cdc592e10b60f9097a7b0d3c59fce29876"
        token.contract_data = {"contract_address": raw_addr}
        token.checksum_address
        mock_checksum.assert_called_once_with(raw_addr)

    def test_deployment_block_raises_error_when_called_on_undeployed_token(
        self, instance_under_test
    ):
        assert not instance_under_test.deployment_receipt
        with pytest.raises(TokenNotDeployed):
            instance_under_test.deployment_block

    def test_deployment_block_is_returned_from_deployment_receipt_attribute(
        self, instance_under_test
    ):
        instance_under_test.deployment_receipt = {"blockNum": 100}
        assert instance_under_test.deployment_block == 100

    @pytest.mark.parametrize(
        "receipt, expected",
        argvalues=[
            (None, False),
            ({}, False),
            ({"blockNum": 100}, True),
            ({"blockNum": None}, False),
        ],
    )
    def test_deployed_property_depends_on_value_of_deployment_receipt(
        self, receipt, expected, instance_under_test
    ):
        instance_under_test.deployment_receipt = receipt
        assert instance_under_test.deployed is expected

    def test_balance_raises_error_if_accessed_before_token_deployment(self, instance_under_test):
        assert instance_under_test.deployment_receipt is None
        with pytest.raises(TokenNotDeployed):
            instance_under_test.balance

    def test_balance_calls_local_rpc_client_func(self, instance_under_test):
        instance_under_test.deployment_receipt = {"blockNum": 100}
        instance_under_test.balance
        instance_under_test._local_rpc_client.balance.assert_called_once_with(
            instance_under_test.address
        )

    @pytest.mark.dependency(name="load_token")
    @pytest.mark.parametrize(
        "file_as_json_str, expected_exc",
        argvalues=[
            (json.dumps({"block": 0, "name": "mytoken"}), TokenFileError),
            (json.dumps({"address": "0x052362263636", "block": 0}), TokenFileError),
            (json.dumps({"address": "0x052362263636", "name": "mytoken"}), TokenFileError),
            ('{"address": "0x00000000", ', TokenFileError),
        ],
        ids=[
            "..the 'address' key is missing",
            "..the 'name' key is missing",
            "..the 'block' key is missing",
            "..the token file is not JSONDecodable",
        ],
    )
    @patch(f"{token_import_path}.pathlib.Path.read_text")
    def test_load_from_file_raises_error_if(
        self, mock_read_text, file_as_json_str, expected_exc, instance_under_test
    ):
        mock_read_text.return_value = file_as_json_str
        with pytest.raises(expected_exc):
            instance_under_test.load_from_file()

    @patch(f"{token_import_path}.pathlib.Path.read_text")
    def test_load_from_file_raises_missing_file_error_if_file_cannot_be_found(
        self, mock_read_text, instance_under_test
    ):
        mock_read_text.side_effect = FileNotFoundError
        with pytest.raises(TokenFileMissing):
            instance_under_test.load_from_file()

    @patch(f"{token_import_path}.to_checksum_address", return_value="my_checksum_addr")
    def test_save_token_overwrites_existing_token_file_on_save(
        self, _, instance_under_test, tmp_path
    ):
        old_text = "old, old, old."
        existing_token_info = tmp_path.joinpath("token.info")
        existing_token_info.touch()
        existing_token_info.write_text(old_text)

        # Inject a deployment receipt, contract data
        instance_under_test.deployment_receipt = {"blockNum": 1}
        instance_under_test.contract_data = {"contract_name": "mytoken"}

        expected_str = json.dumps({"name": "mytoken", "address": "my_checksum_addr", "block": 1})
        instance_under_test.save_token()

        assert json.loads(tmp_path.joinpath("token.info").read_text()) == json.loads(expected_str)

    @patch(f"{token_import_path}.to_checksum_address", return_value="my_checksum_addr")
    def test_save_token_creates_file_if_it_does_not_exist_already(
        self, _, instance_under_test, tmp_path
    ):
        # Inject a deployment receipt, contract data
        instance_under_test.deployment_receipt = {"blockNum": 1}
        instance_under_test.contract_data = {"contract_name": "mytoken"}

        expected_str = json.dumps({"name": "mytoken", "address": "my_checksum_addr", "block": 1})
        instance_under_test.save_token()

        assert json.loads(tmp_path.joinpath("token.info").read_text()) == json.loads(expected_str)

    @patch(f"{token_import_path}.to_checksum_address", return_value="my_checksum_addr")
    @pytest.mark.dependency(depends=["load_token"])
    def test_save_token_create_loadable_token_file(self, _, instance_under_test, tmp_path):
        # Inject a deployment receipt, contract data
        instance_under_test.deployment_receipt = {"blockNum": 1}
        instance_under_test.contract_data = {"contract_name": "mytoken"}

        expected_dict = {"name": "mytoken", "address": "my_checksum_addr", "block": 1}
        instance_under_test.save_token()
        assert instance_under_test.load_from_file() == expected_dict

    @pytest.mark.parametrize(
        "reuse_token",
        argvalues=[True, False],
        ids=[
            "reuse_existing called if reuse_token is True",
            "deploy_new called if reuse_token is False",
        ],
    )
    @patch(f"{token_import_path}.Token.deploy_new")
    @patch(f"{token_import_path}.Token.use_existing")
    @patch(
        f"scenario_player.utils.configuration.token.TokenConfig.reuse_token",
        new_callable=PropertyMock,
    )
    def test_init_calls_appropriate_method_depending_on_reuse_settings_in_config(
        self,
        mock_reuse_token,
        mock_use_existing,
        mock_deploy_new,
        reuse_token,
        instance_under_test,
    ):
        mock_reuse_token.return_value = reuse_token

        instance_under_test.init()

        if reuse_token:
            mock_use_existing.assert_called_once()
        else:
            mock_deploy_new.assert_called_once()

    @patch(f"{token_import_path}.Token.load_from_file", side_effect=Sentinel)
    def test_use_exising_loads_token_info_file(self, _, instance_under_test):
        with pytest.raises(Sentinel):
            instance_under_test.use_existing()

    @patch(f"{token_import_path}.check_address_has_code")
    @patch(
        f"{token_import_path}.Token.load_from_file",
        return_value={"address": None, "name": None, "block": 1},
    )
    def test_uses_existing_raises_error_if_address_has_no_sourcecode(
        self, _, mock_check_address, instance_under_test
    ):
        def raise_exc(*args, **kwargs):
            raise AddressWithoutCode

        mock_check_address.side_effect = raise_exc
        with pytest.raises(TokenSourceCodeDoesNotExist):
            instance_under_test.use_existing()

    @patch(f"{token_import_path}.to_checksum_address", side_effect=lambda x: "checksummed_" + x)
    @patch(f"{token_import_path}.check_address_has_code")
    @patch(f"{token_import_path}.Token.load_from_file")
    def test_use_existing_assigns_contract_data_and_deployment_receipt_correctly(
        self, mock_load_from_file, _, __, instance_under_test
    ):
        loaded_token_info = {"address": "my_address", "name": "my_token_name", "block": 1}
        mock_load_from_file.return_value = loaded_token_info

        class MockContractProxy:
            name = "my_deployed_token_name"
            symbol = "token_symbol"

        instance_under_test._local_contract_manager.get_contract.return_value = MockContractProxy

        expected_deployment_receipt = {"blockNum": loaded_token_info["block"]}
        expected_contract_data = {
            "token_contract": loaded_token_info["address"],
            "name": MockContractProxy.name,
        }

        checksummed_addr, block = instance_under_test.use_existing()

        assert checksummed_addr == "checksummed_" + loaded_token_info["address"]
        assert block == loaded_token_info["block"]

        assert instance_under_test.deployment_receipt == expected_deployment_receipt
        assert instance_under_test.contract_data == expected_contract_data

    @pytest.mark.parametrize(
        "exc",
        argvalues=[
            HTTPError,
            ConnectionError,
            ConnectTimeout,
            Timeout,
            ReadTimeout,
            RetryError,
            SSLError,
            ProxyError,
            RequestException,
        ],
    )
    @patch(f"{token_import_path}.ServiceInterface.request")
    def test_deploy_new_does_not_handle_request_exceptions(
        self, mocked_session, exc, instance_under_test
    ):
        mocked_session.side_effect = exc
        with pytest.raises(exc):
            instance_under_test.deploy_new()

    @patch(f"{token_import_path}.to_checksum_address", side_effect=lambda x: "checksummed_" + x)
    @patch(f"{token_import_path}.ServiceInterface.post")
    def test_deploy_new_assigns_contract_data_and_deployment_receipt_from_request(
        self, mock_request, _, instance_under_test
    ):
        json_resp = {
            "contract": {"contract_name": "the_token", "contract_address": "the_address"},
            "receipt": {"blockNum": 111},
        }

        class MockResp:
            def json(self):
                return json_resp

        expected_params = {
            "constructor_args": {
                "decimals": instance_under_test.decimals,
                "name": instance_under_test.name,
                "symbol": instance_under_test.symbol,
            },
            "token_name": instance_under_test.name,
        }

        mock_request.return_value = MockResp()

        address, deployment_block = instance_under_test.deploy_new()

        assert address == json_resp["contract"]["contract_address"]
        assert deployment_block == json_resp["receipt"]["blockNum"]

        assert instance_under_test.deployment_receipt == json_resp["receipt"]
        assert instance_under_test.contract_data == json_resp["contract"]

        mock_request.assert_called_once_with("spaas://rpc/token", params=expected_params)

    @pytest.mark.parametrize("reuse_token", argvalues=[True, False])
    @patch(f"{token_import_path}.ServiceInterface.request")
    @patch(f"{token_import_path}.Token.save_token")
    @patch(f"{token_import_path}.to_checksum_address", side_effect=lambda x: "checksummed")
    @patch(
        f"scenario_player.utils.configuration.token.TokenConfig.reuse_token",
        new_callable=PropertyMock,
    )
    def test_deploy_new_calls_save_token_depending_on_reuse_token_property(
        self, mock_reuse_token, _, mock_save_token, mock_request, reuse_token, instance_under_test
    ):
        json_resp = {"contract": {}, "receipt": {}}

        class MockResp:
            def json(self):
                return json_resp

        mock_reuse_token.return_value = reuse_token
        mock_request.return_value = MockResp()
        mock_save_token.side_effect = Sentinel
        try:
            instance_under_test.deploy_new()
        except Sentinel:
            if reuse_token:
                return
            pytest.fail(f"save_token called, but reuse_token is {reuse_token}")

    @staticmethod
    def setup_instance_with_balance(
        instance, current_balance, balance_min=1000, balance_fund=10000
    ):
        # Set up rpc client balance call
        instance._local_rpc_client.balance.return_value = current_balance

        # Inject deployment receipt
        instance.deployment_receipt = {"blockNum": 1}

        # Inject mint settings
        instance.config.dict = {"balance_min": balance_min, "balance_fund": balance_fund}
        return instance

    @patch(f"{token_import_path}.ServiceInterface.request")
    def test_mint_is_a_no_op_if_balance_is_sufficient(self, mock_request, instance_under_test):
        instance_under_test = self.setup_instance_with_balance(instance_under_test, 100000)

        assert instance_under_test.mint("the_address", 100) is None
        assert mock_request.called is False

    @patch(f"{token_import_path}.ServiceInterface.post", side_effect=Sentinel)
    def test_mint_correctly_calculates_amount_to_mint(self, mock_request, instance_under_test):
        instance_under_test = self.setup_instance_with_balance(instance_under_test, 100)

        # balance = 100, min_balance = 1000, max_funding = 10000
        # max_fund - balance = expected_amount
        # 10000 - 100 = 9900
        # #maths #magic
        expected_amount = 9900

        expected_params = {
            "action": "mintFor",
            "gas_limit": 100,
            "amount": expected_amount,
            "target_address": "the_address",
        }

        with pytest.raises(Sentinel):
            instance_under_test.mint("the_address", 100)

        mock_request.assert_called_once_with("spaas://rpc/token/mint", params=expected_params)
