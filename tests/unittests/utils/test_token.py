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
from scenario_player.utils.token import Contract, Token, UserDepositContract

token_import_path = "scenario_player.utils.token"
token_config_import_path = "scenario_player.utils.configuration.token"


class Sentinel(Exception):
    """Raised when it's desired to exit a method under test early."""


@pytest.fixture
def runner(dummy_scenario_runner, minimal_yaml_dict, token_info_path, tmp_path):
    token_config = TokenConfig(minimal_yaml_dict, token_info_path)
    dummy_scenario_runner.yaml.spaas = SPaaSConfig(minimal_yaml_dict)
    dummy_scenario_runner.yaml.spaas.rpc.client_id = "the_client_id"
    dummy_scenario_runner.yaml.token = token_config

    dummy_scenario_runner.token = Token(dummy_scenario_runner, tmp_path)

    return dummy_scenario_runner


@pytest.fixture
def token_instance(runner, tmp_path):
    return Token(runner, tmp_path)


@pytest.fixture
def contract_instance(runner, tmp_path):
    return Contract(runner, "my_address")


class TestContract:
    @patch(f"{token_import_path}.ServiceInterface")
    def test_constructor_loads_attributes_correctly(self, mock_interface, runner, tmp_path):
        """The following attributes are loaded correctly from the given parameters:

            - :attr:`Contract.interface` is an instance of :class:`ServiceInterface`
                and constructed using the passed `yaml_config` paramter.

            - :attr:`Contract._local_rpc_client` is loaded from :attr:`runner.client`

            - :attr:`Contract._local_contract_manager` is loaded from
                :attr:`runner.client.contract_manager`

            - :attr:`Contract.config` is a reference to `runner.yaml`.
        """
        iface = object()
        mock_interface.return_value = iface
        contract = Contract(runner, tmp_path)

        mock_interface.assert_called_once_with(runner.yaml.spaas)
        assert contract.interface == iface

        assert contract._local_rpc_client == runner.client
        assert contract._local_contract_manager == runner.contract_manager
        assert contract.config == runner.yaml

    def test_address_property_returns_from_private_attribute(self, contract_instance):
        contract_instance._address = "khashyyk"
        assert contract_instance.address == "khashyyk"

    @patch(f"{token_import_path}.to_checksum_address", return_value="checksummed")
    def test_checksum_address_uses_to_checksum_address(self, mock_checksum, contract_instance):
        assert contract_instance.checksum_address == "checksummed"
        mock_checksum.assert_called_once_with(contract_instance.address)

    def test_balance_calls_local_rpc_client_func(self, contract_instance):
        contract_instance._local_rpc_client.balance.return_value = 666
        assert contract_instance.balance == 666
        contract_instance._local_rpc_client.balance.assert_called_once_with(
            contract_instance.address
        )

    @staticmethod
    def setup_instance_with_balance(instance, current_balance):
        # Set up rpc client balance call
        instance._local_rpc_client.balance.return_value = current_balance

        return instance

    @patch(f"{token_import_path}.ServiceInterface.request")
    def test_mint_is_a_no_op_if_balance_is_sufficient(self, mock_request, contract_instance):
        contract_instance = self.setup_instance_with_balance(contract_instance, 100000)

        assert contract_instance.mint("the_address") is None
        assert mock_request.called is False

    @patch(f"{token_import_path}.ServiceInterface.post", side_effect=Sentinel)
    def test_mint_correctly_calculates_amount_to_mint(self, mock_request, contract_instance):
        contract_instance = self.setup_instance_with_balance(contract_instance, 100)

        expected_amount = contract_instance.config.token.max_funding - 100

        expected_params = {
            "client_id": "the_client_id",
            "gas_limit": contract_instance.config.gas_limit,
            "amount": expected_amount,
            "target_address": "the_address",
            "contract_address": "my_address",
        }

        with pytest.raises(Sentinel):
            contract_instance.mint("the_address")

        mock_request.assert_called_once_with("spaas://rpc/token/mint", json=expected_params)


@pytest.mark.dependency(name="TestClass")
class TestToken:
    def test_constructor_loads_attributes_correctly(self, runner, tmp_path):
        """The following attributes are loaded correctly from the given parameters:

            - :attr:`Token._token_file` is constructed by joining the `data_path`
                parameter with `token.info`.

            - :attr:`Token.contract_data` is initialized as an empty dict

            - :attr:`Token.deployment_receipt` is initialized as None.

        """
        token = Token(runner, tmp_path)
        assert token._token_file == tmp_path.joinpath("token.info")
        assert token.contract_data == {}
        assert token.deployment_receipt is None

    @pytest.mark.parametrize("prop", argvalues=["name", "symbol", "decimals"])
    @patch(f"{token_config_import_path}.TokenConfig.decimals", new_callable=PropertyMock)
    @patch(f"{token_config_import_path}.TokenConfig.symbol", new_callable=PropertyMock)
    @patch(f"{token_config_import_path}.TokenConfig.name", new_callable=PropertyMock)
    def test_properties_correctly_map_to_property_on_token_config(
        self,
        m_name,
        m_symbol,
        m_decimals,
        prop,
        runner,
        tmp_path,
        token_info_path,
        minimal_yaml_dict,
    ):
        mocked_properties = {"name": m_name, "symbol": m_symbol, "decimals": m_decimals}
        runner.yaml.token = TokenConfig(minimal_yaml_dict, token_info_path)
        token = Token(runner, tmp_path)
        getattr(token, prop)
        assert len(mocked_properties[prop].mock_calls) == 1

    @patch(f"{token_config_import_path}.TokenConfig.address", new_callable=PropertyMock)
    def test_address_is_fetched_from_contract_data_if_available(
        self, mock_address, runner, tmp_path
    ):
        token = Token(runner, tmp_path)
        token.contract_data = {"address": 100}
        mock_address.return_value = 200
        assert token.address == 100

    @patch(f"{token_config_import_path}.TokenConfig.address", new_callable=PropertyMock)
    def test_address_is_fetched_from_token_config_if_no_contract_data_available(
        self, mock_address, runner, tmp_path
    ):
        token = Token(runner, tmp_path)
        mock_address.return_value = 100
        assert token.address == 100

    @patch(f"{token_import_path}.to_checksum_address")
    def test_checksum_address_property_address_in_token_config_if_token_is_not_deployed(
        self, mock_to_checksum, token_instance
    ):
        # inject address key to token config
        token_instance.config.token.dict["address"] = "my_addr"
        assert token_instance.contract_data == {}
        token_instance.checksum_address
        mock_to_checksum.assert_called_once_with("my_addr")

    @patch(f"{token_import_path}.to_checksum_address")
    def test_checksum_address_returns_checksummed_raw_address_from_contract_data_if_available(
        self, mock_checksum, runner, tmp_path
    ):
        token = Token(runner, tmp_path)

        raw_addr = "0x12ae66cdc592e10b60f9097a7b0d3c59fce29876"
        token.contract_data = {"address": raw_addr}
        token.checksum_address
        mock_checksum.assert_called_once_with(raw_addr)

    def test_deployment_block_raises_error_when_called_on_undeployed_token(self, token_instance):
        assert not token_instance.deployment_receipt
        with pytest.raises(TokenNotDeployed):
            token_instance.deployment_block

    def test_deployment_block_is_returned_from_deployment_receipt_attribute(self, token_instance):
        token_instance.deployment_receipt = {"blockNumber": 100}
        assert token_instance.deployment_block == 100

    @pytest.mark.parametrize(
        "receipt, expected",
        argvalues=[
            (None, False),
            ({}, False),
            ({"blockNumber": 100}, True),
            ({"blockNumber": None}, False),
        ],
    )
    def test_deployed_property_depends_on_value_of_deployment_receipt(
        self, receipt, expected, token_instance
    ):
        token_instance.deployment_receipt = receipt
        assert token_instance.deployed is expected

    def test_balance_raises_error_if_accessed_before_token_deployment(self, token_instance):
        assert token_instance.deployment_receipt is None
        with pytest.raises(TokenNotDeployed):
            token_instance.balance

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
        self, mock_read_text, file_as_json_str, expected_exc, token_instance
    ):
        mock_read_text.return_value = file_as_json_str
        with pytest.raises(expected_exc):
            token_instance.load_from_file()

    @patch(f"{token_import_path}.pathlib.Path.read_text")
    def test_load_from_file_raises_missing_file_error_if_file_cannot_be_found(
        self, mock_read_text, token_instance
    ):
        mock_read_text.side_effect = FileNotFoundError
        with pytest.raises(TokenFileMissing):
            token_instance.load_from_file()

    @patch(f"{token_import_path}.to_checksum_address", return_value="my_checksum_addr")
    def test_save_token_overwrites_existing_token_file_on_save(self, _, token_instance, tmp_path):
        old_text = "old, old, old."
        existing_token_info = tmp_path.joinpath("token.info")
        existing_token_info.touch()
        existing_token_info.write_text(old_text)

        # Inject a deployment receipt, contract data
        token_instance.deployment_receipt = {"blockNumber": 1}
        token_instance.contract_data = {"name": "mytoken"}

        expected_str = json.dumps({"name": "mytoken", "address": "my_checksum_addr", "block": 1})
        token_instance.save_token()

        assert json.loads(tmp_path.joinpath("token.info").read_text()) == json.loads(expected_str)

    @patch(f"{token_import_path}.to_checksum_address", return_value="my_checksum_addr")
    def test_save_token_creates_file_if_it_does_not_exist_already(
        self, _, token_instance, tmp_path
    ):
        # Inject a deployment receipt, contract data
        token_instance.deployment_receipt = {"blockNumber": 1}
        token_instance.contract_data = {"name": "mytoken"}

        expected_str = json.dumps({"name": "mytoken", "address": "my_checksum_addr", "block": 1})
        token_instance.save_token()

        assert json.loads(tmp_path.joinpath("token.info").read_text()) == json.loads(expected_str)

    @patch(f"{token_import_path}.to_checksum_address", return_value="my_checksum_addr")
    @pytest.mark.dependency(depends=["load_token"])
    def test_save_token_create_loadable_token_file(self, _, token_instance, tmp_path):
        # Inject a deployment receipt, contract data
        token_instance.deployment_receipt = {"blockNumber": 1}
        token_instance.contract_data = {"name": "mytoken"}

        expected_dict = {"name": "mytoken", "address": "my_checksum_addr", "block": 1}
        token_instance.save_token()
        assert token_instance.load_from_file() == expected_dict

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
        self, mock_reuse_token, mock_use_existing, mock_deploy_new, reuse_token, token_instance
    ):
        mock_reuse_token.return_value = reuse_token

        token_instance.init()

        if reuse_token:
            mock_use_existing.assert_called_once()
        else:
            mock_deploy_new.assert_called_once()

    @patch(f"{token_import_path}.Token.load_from_file", side_effect=Sentinel)
    def test_use_exising_loads_token_info_file(self, _, token_instance):
        with pytest.raises(Sentinel):
            token_instance.use_existing()

    @patch(f"{token_import_path}.check_address_has_code")
    @patch(
        f"{token_import_path}.Token.load_from_file",
        return_value={"address": None, "name": None, "block": 1},
    )
    def test_uses_existing_raises_error_if_address_has_no_sourcecode(
        self, _, mock_check_address, token_instance
    ):
        def raise_exc(*args, **kwargs):
            raise AddressWithoutCode

        mock_check_address.side_effect = raise_exc
        with pytest.raises(TokenSourceCodeDoesNotExist):
            token_instance.use_existing()

    @patch(f"{token_import_path}.to_checksum_address", side_effect=lambda x: "checksummed_" + x)
    @patch(f"{token_import_path}.check_address_has_code")
    @patch(f"{token_import_path}.Token.load_from_file")
    def test_use_existing_assigns_contract_data_and_deployment_receipt_correctly(
        self, mock_load_from_file, _, __, token_instance
    ):
        loaded_token_info = {"address": "my_address", "name": "my_token_name", "block": 1}
        mock_load_from_file.return_value = loaded_token_info

        class MockContractProxy:
            name = "my_deployed_token_name"
            symbol = "token_symbol"

        token_instance._local_contract_manager.get_contract.return_value = MockContractProxy

        expected_deployment_receipt = {"blockNum": loaded_token_info["block"]}
        expected_contract_data = {
            "token_contract": loaded_token_info["address"],
            "name": MockContractProxy.name,
        }

        checksummed_addr, block = token_instance.use_existing()

        assert checksummed_addr == "checksummed_" + loaded_token_info["address"]
        assert block == loaded_token_info["block"]

        assert token_instance.deployment_receipt == expected_deployment_receipt
        assert token_instance.contract_data == expected_contract_data

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
        self, mocked_session, exc, token_instance
    ):
        mocked_session.side_effect = exc
        with pytest.raises(exc):
            token_instance.deploy_new()

    @patch(f"{token_import_path}.to_checksum_address", side_effect=lambda x: "checksummed_" + x)
    @patch(f"{token_import_path}.ServiceInterface.post")
    def test_deploy_new_assigns_contract_data_and_deployment_receipt_from_request(
        self, mock_request, _, token_instance
    ):
        json_resp = {
            "contract": {"name": "the_token", "address": "the_address"},
            "deployment_block": 111,
        }

        class MockResp:
            def json(self):
                return json_resp

        expected_params = {
            "client_id": "the_client_id",
            "constructor_args": {
                "decimals": token_instance.decimals,
                "name": token_instance.name,
                "symbol": token_instance.symbol,
            },
            "token_name": token_instance.name,
        }

        mock_request.return_value = MockResp()

        address, deployment_block = token_instance.deploy_new()

        assert address == json_resp["contract"]["address"]
        assert deployment_block == json_resp["deployment_block"]

        assert token_instance.deployment_receipt == {"blockNumber": json_resp["deployment_block"]}
        assert token_instance.contract_data == json_resp["contract"]

        mock_request.assert_called_once_with("spaas://rpc/token", json=expected_params)

    @pytest.mark.parametrize("reuse_token", argvalues=[True, False])
    @patch(f"{token_import_path}.ServiceInterface.request")
    @patch(f"{token_import_path}.Token.save_token")
    @patch(f"{token_import_path}.to_checksum_address", side_effect=lambda x: "checksummed")
    def test_deploy_new_calls_save_token_depending_on_reuse_token_property(
        self, _, mock_save_token, mock_request, reuse_token, token_instance
    ):
        json_resp = {"contract": {}, "deployment_block": 1}

        class MockResp:
            def json(self):
                return json_resp

        token_instance.config.token.dict["reuse"] = reuse_token
        if reuse_token:
            token_instance.config.token._token_file.touch()

        mock_request.return_value = MockResp()
        mock_save_token.side_effect = Sentinel
        try:
            token_instance.deploy_new()
        except Sentinel:
            if reuse_token:
                return
            pytest.fail(f"save_token called, but reuse_token is {reuse_token}")
