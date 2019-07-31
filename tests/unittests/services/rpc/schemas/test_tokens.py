from unittest import mock

import flask
import pytest

from raiden.network.rpc.client import JSONRPCClient
from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.schemas.base import RPCCreateResourceSchema
from scenario_player.services.rpc.schemas.tokens import TokenCreateSchema, TokenMintSchema
from scenario_player.services.rpc.utils import RPCRegistry


@pytest.fixture
def hexed_client_id():
    return str(b"test-client-id".hex())


@pytest.fixture
def base_request_params(hexed_client_id):
    """Parameters required by the Schemas under testing in this module, but not under testing themselves.

    i.e. they're already tested somewhere else.
    """
    return {"client_id": hexed_client_id}


@pytest.fixture
def deserialized_base_params(app, base_request_params):
    deserialized = dict(base_request_params)
    deserialized["client"], _ = app.config["rpc-client"][base_request_params["client_id"]]
    return deserialized


@pytest.fixture
def app(hexed_client_id):

    bp = flask.Blueprint("test_views", __name__)

    @bp.route("/test-create", methods=["POST"])
    def create_token():
        TokenCreateSchema().validate_and_deserialize(flask.request.form)
        return "ok"

    @bp.route("/test-mint", methods=["POST"])
    def mint_token():
        TokenMintSchema().validate_and_deserialize(flask.request.form)
        return "ok"

    registry = RPCRegistry()
    registry.dict[hexed_client_id] = mock.MagicMock(spec=JSONRPCClient)

    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.config["rpc-client"] = registry

    app.register_blueprint(bp)

    return app


@pytest.mark.parametrize(
    "schema",
    argvalues=[TokenCreateSchema(), TokenMintSchema()],
    ids=["TokenCreateSchema", "TokenMintSchema"],
)
class TestSchemaDefinition:
    def test_tx_hash_is_bytesfield(self, schema):
        assert isinstance(schema._declared_fields["tx_hash"], BytesField)

    def test_tx_hash_is_dump_only(self, schema):
        assert schema._declared_fields["tx_hash"].dump_only is True

    def test_schema_inherits_from_rpccreateresourceschema(self, schema):
        assert isinstance(schema, RPCCreateResourceSchema)


class TestTokenCreateSchema:
    @pytest.mark.parametrize("field", ["token_name", "constructor_args"])
    def test_field_is_load_only(self, field):
        assert TokenCreateSchema._declared_fields[field].load_only is True

    @pytest.mark.parametrize(
        "input_dict, expected",
        argvalues=[
            (
                {
                    "constructor_args": {
                        "decimals": 6789,
                        "name": "TokenName",
                        "symbol": "TokenSymbol",
                    },
                    "token_name": "SuperToken",
                },
                {
                    "constructor_args": {
                        "decimals": 6789,
                        "name": "TokenName",
                        "symbol": "TokenSymbol",
                    },
                    "token_name": "SuperToken",
                },
            ),
            (
                {
                    "constructor_args": {
                        "decimals": 6789,
                        "name": "TokenName",
                        "symbol": "TokenSymbol",
                    }
                },
                {
                    "constructor_args": {
                        "decimals": 6789,
                        "name": "TokenName",
                        "symbol": "TokenSymbol",
                    },
                    "token_name": None,
                },
            ),
        ],
        ids=["All fields given", "token_name field missing assigns it None"],
    )
    def test_validate_and_deserialize_returns_expected_dict(
        self, input_dict, expected, app, base_request_params, deserialized_base_params
    ):
        base_request_params.update(input_dict)
        deserialized_base_params.update(expected)

        with app.app_context():
            assert (
                TokenCreateSchema().validate_and_deserialize(base_request_params)
                == deserialized_base_params
            )

    @pytest.mark.parametrize(
        "input_dict",
        argvalues=[
            {},
            {"constructor_args": {"name": "TokenName", "symbol": "TokenSymbol"}},
            {"constructor_args": {"decimals": 6789, "symbol": "TokenSymbol"}},
            {"constructor_args": {"decimals": 6789, "name": "TokenName"}},
            {"constructor_args": {"decimals": 6789, "name": 80085, "symbol": "TokenSymbol"}},
            {
                "constructor_args": {
                    "decimals": "fifty",
                    "name": "TokenName",
                    "symbol": "TokenSymbol",
                }
            },
            {"constructor_args": {"decimals": 6789, "name": "TokenName", "symbol": 8000}},
            {
                "constructor_args": {
                    "decimals": 6789,
                    "name": "TokenName",
                    "symbol": "TokenSymbol",
                },
                "token_name": 5000,
            },
        ],
        ids=[
            "constructor_args are required",
            "constructor_args requires decimals key",
            "constructor_args requires name key",
            "constructor_args requires symbol key",
            "constructor_args.deccimals must be an integer",
            "constructor_args.name must be a string",
            "constructor_args.symbol must be a string",
            "token_name must be a string",
        ],
    )
    def test_validate_and_deserialize_raises_excpetions_on_faulty_input(self, input_dict, app):
        with app.test_client() as c:
            resp = c.post("/test-create", json=input_dict)
            assert "400 Bad Request".lower() in resp.status.lower()


class TestTokenMintSchema:
    @pytest.mark.parametrize("field", ["token_address", "mint_target", "amount"])
    def test_field_is_load_only(self, field):
        assert TokenMintSchema._declared_fields[field].load_only is True

    def test_validate_and_deserialize_returns_expected_dict(
        self, app, base_request_params, deserialized_base_params
    ):
        input_dict = {"token_address": "0x0002", "mint_target": "0x0001", "amount": "123.5"}
        expected = {"token_address": "0x0002", "mint_target": "0x0001", "amount": 123.5}
        base_request_params.update(input_dict)
        deserialized_base_params.update(expected)

        with app.app_context():
            assert (
                TokenMintSchema().validate_and_deserialize(base_request_params)
                == deserialized_base_params
            )

    @pytest.mark.parametrize(
        "input_dict",
        argvalues=[
            {"mint_target": "0x0001", "amount": "123.5"},
            {"token_address": "0x0002", "amount": "123.5"},
            {"token_address": "0x0002", "mint_target": "0x0001"},
            {"token_address": "0x0002", "mint_target": "0x0001", "amount": "123.5"},
            {"token_address": "0x0002", "mint_target": 1000, "amount": "123.5"},
            {"token_address": 1000, "mint_target": "0x0001", "amount": "123.5"},
        ],
        ids=[
            "token_address required",
            "mint_target required",
            "amount required",
            "amount must be a number",
            "mint_target must be a string",
            "token_address must be a string",
        ],
    )
    def test_validate_and_deserialize_raises_excpetions_on_faulty_input(self, input_dict, app):
        with app.test_client() as c:
            resp = c.post("/test-mint", data=input_dict)
            assert "400 Bad Request".lower() in resp.status.lower()
