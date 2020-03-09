import json
from unittest.mock import MagicMock, patch

import flask
import pytest
from eth_utils import to_canonical_address

from scenario_player.services.rpc.blueprints.tokens import TRANSACT_ACTIONS, tokens_blueprint
from scenario_player.services.rpc.schemas.tokens import ContractTransactSchema, TokenCreateSchema
from scenario_player.services.rpc.utils import RPCClient, RPCRegistry

pytestmark = pytest.mark.skip(
    reason="about to be removed, see https://github.com/raiden-network/scenario-player/issues/502"
)

rpc_blueprints_module_path = "scenario_player.services.rpc.blueprints"


class MockTokenProxy:
    address = "deployed_contract_address"


@pytest.fixture
def hexed_client_id():
    return str(b"test-client-id".hex())


@pytest.fixture
def create_token_params(hexed_client_id):
    return {
        "client_id": hexed_client_id,
        "constructor_args": {"decimals": 66, "name": "token_name", "symbol": "token_symbol"},
        "token_name": "non-constructor-token_name",
    }


@pytest.fixture
def deserialized_create_token_params(create_token_params, app):
    deserialized = dict(create_token_params)
    deserialized["client"] = app.config["rpc-client"].dict[deserialized["client_id"]]
    return deserialized


@pytest.fixture
def mint_token_params(hexed_client_id):
    return {
        "client_id": hexed_client_id,
        "contract_address": "0x1111111111111111111111111111111111111111",
        "target_address": "0x2222222222222222222222222222222222222222",
        "amount": 5,
    }


@pytest.fixture
def deserialized_mint_token_params(app, mint_token_params):
    deserialized = dict(mint_token_params)
    deserialized["client"] = app.config["rpc-client"].dict[deserialized["client_id"]]
    return deserialized


@pytest.fixture
def app(hexed_client_id):
    rpc_client = MagicMock(client_id=hexed_client_id)
    rpc_client.deploy_single_contract.return_value = (MockTokenProxy(), {"blockNumber": 100})

    registry = RPCRegistry()
    registry.dict[hexed_client_id] = rpc_client

    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.config["rpc-client"] = registry

    app.register_blueprint(tokens_blueprint)

    return app


@pytest.mark.dependency(name="tokens_blueprint_loaded")
def test_token_blueprint_is_loaded(transaction_service_client):
    assert "tokens_blueprint" in transaction_service_client.application.blueprints


@pytest.mark.dependency(depends=["tokens_blueprint_loaded"])
@patch(
    f"{rpc_blueprints_module_path}.tokens.to_checksum_address", return_value="checksummed_address"
)
@patch(
    f"{rpc_blueprints_module_path}.tokens.ContractManager.get_contract",
    return_value={"CustomToken": "cm_token"},
)
@patch(f"{rpc_blueprints_module_path}.tokens.token_create_schema", spec=TokenCreateSchema)
class TestDeployTokenEndpoint:
    @pytest.fixture(autouse=True)
    def setup_create_token_tests(
        self, app, hexed_client_id, create_token_params, deserialized_create_token_params
    ):
        self.app = app
        self.request_params = create_token_params
        self.deserialized_params = deserialized_create_token_params
        self.client_id = hexed_client_id

    def test_endpoint_calls_validate_and_deserialize_of_its_schema(self, mock_schema, _, __):
        mock_schema.validate_and_deserialize.return_value = self.deserialized_params
        with self.app.test_client() as c:
            c.post("/rpc/contract", json=self.request_params)
        mock_schema.validate_and_deserialize.assert_called_once_with(self.request_params)

    def test_endpoint_returns_jsonified_data(self, mock_schema, _, __):
        mock_schema.validate_and_deserialize.return_value = self.deserialized_params

        mock_schema.dump.return_value = {"data": "ok"}
        with self.app.test_client() as c:
            resp = c.post("/rpc/contract", json=self.request_params)
            assert mock_schema.dump.called
            assert resp.data == b'{"data":"ok"}\n'

    def test_result_returns_expected_dict(self, mock_schema, _, __):
        expected = {
            "contract": {
                "address": "checksummed_address",
                "name": self.deserialized_params["token_name"],
            },
            "deployment_block": 100,
        }

        mock_schema.validate_and_deserialize.return_value = self.deserialized_params

        def return_input(value, *_, **__):
            return value

        mock_schema.dump.side_effect = return_input

        with self.app.test_client() as c:
            resp = c.post("/rpc/contract", json=self.request_params)
            assert resp.status == "200 OK", resp.data
            assert json.loads(resp.data) == expected

    def test_endpoint_calls_deploy_single_contract_of_rpc_client_with_constructor_args(
        self, mock_schema, _, __
    ):

        mock_schema.validate_and_deserialize.return_value = self.deserialized_params

        mocked_client = self.app.config["rpc-client"].dict[self.client_id]

        with self.app.test_client() as c:
            print(self.request_params)
            resp = c.post("/rpc/contract", json=self.request_params)
            assert resp.status == "200 OK"

        expected_args = self.deserialized_params["constructor_args"]

        mocked_client.deploy_single_contract.assert_called_once_with(
            "CustomToken",
            {"CustomToken": "cm_token"},
            constructor_parameters=(
                1,
                expected_args["decimals"],
                expected_args["name"],
                expected_args["symbol"],
            ),
        )


@pytest.mark.parametrize("action", argvalues=["mint", "allowance", "deposit"])
@pytest.mark.dependency(name="tokens_blueprint_loaded")
@patch(f"{rpc_blueprints_module_path}.tokens.token_transact_schema", spec=ContractTransactSchema)
@patch(
    f"{rpc_blueprints_module_path}.tokens.ContractManager.get_contract_abi",
    return_value="token_abi",
)
class TestTokenEndpoint:

    ENDPOINT_TO_ACTION = {"/rpc/contract/mint": "mintFor", "/rpc/contract/allowance": "approve"}

    @pytest.fixture(autouse=True)
    def setup_mint_token_tests(
        self, app, mint_token_params, deserialized_mint_token_params, hexed_client_id
    ):
        self.request_params = mint_token_params
        self.deserialized_params = deserialized_mint_token_params
        self.app = app
        self.client_id = hexed_client_id
        self.rpc_client = self.app.config["rpc-client"].dict[self.client_id]
        self.rpc_client.new_contract_proxy.return_value = "test-proxy"
        self.rpc_client.transact.return_value = b"tx_hash"
        self.rpc_client.web3.eth.getBlock.return_value = {"hash": 1, "number": 123}

    def test_the_endpoint_calls_validate_and_deserialize_of_its_schema(
        self, _, mock_schema, action
    ):
        mock_schema.validate_and_deserialize.return_value = self.deserialized_params
        with self.app.test_client() as c:
            c.post(f"/rpc/contract/{action}", json=self.request_params)

        mock_schema.validate_and_deserialize.assert_called_once_with(self.request_params)

    def test_endpoint_fetches_proxy_using_the_contract_address_provided(
        self, _, mock_schema, action
    ):
        mock_schema.validate_and_deserialize.return_value = self.deserialized_params

        with self.app.test_client() as c:
            c.post(f"/rpc/contract/{action}", json=self.request_params)

        self.app.config["rpc-client"].dict[
            self.client_id
        ].new_contract_proxy.assert_called_once_with(
            abi="token_abi",
            contract_address=to_canonical_address(self.deserialized_params["contract_address"]),
        )

    def test_endpoint_calls_proxy_contract_transact_with_passed_request_parameters(
        self, _, mock_schema, action
    ):
        mock_schema.validate_and_deserialize.return_value = self.deserialized_params

        expected_action, contract, _ = TRANSACT_ACTIONS[action]

        with self.app.test_client() as c:
            c.post(f"/rpc/contract/{action}", json=self.request_params)

        amount = self.deserialized_params["amount"]
        target = self.deserialized_params["target_address"]
        args = target, amount
        if action == "mint":
            args = amount, target

        assert self.rpc_client.transact.called
        assert self.rpc_client.transact.call_args[0][0].data.args == args

    def test_endpoint_returns_jsonified_data(self, _, mock_schema, action):
        mock_schema.validate_and_deserialize.return_value = self.deserialized_params
        mock_schema.dump.side_effect = lambda x: x

        with self.app.test_client() as c:
            resp = c.post(f"/rpc/contract/{action}", json=self.request_params)
            assert resp.data == b'{"tx_hash":"tx_hash"}\n'
