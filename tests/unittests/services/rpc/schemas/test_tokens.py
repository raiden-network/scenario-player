from unittest import mock

import flask
import marshmallow as ma
import pytest

from raiden.network.rpc.client import JSONRPCClient
from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.schemas.base import RPCCreateResourceSchema
from scenario_player.services.rpc.schemas.tokens import (
    ConstructorArgsSchema,
    ContractSchema,
    TokenCreateSchema,
    TokenMintSchema,
)
from scenario_player.services.rpc.utils import RPCClient, RPCRegistry


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
    deserialized["client"] = app.config["rpc-client"][base_request_params["client_id"]]
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
    registry.dict[hexed_client_id] = mock.MagicMock(spec=RPCClient, client_id=hexed_client_id)

    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.config["rpc-client"] = registry

    app.register_blueprint(bp)

    return app


class TestConstructorArgsSchema:
    @pytest.mark.parametrize("field", ["decimals", "name", "symbol"])
    def test_field_is_required(self, field):
        assert ConstructorArgsSchema._declared_fields[field].required is True

    @pytest.mark.parametrize(
        "field, field_type",
        [
            ("decimals", ma.fields.Integer),
            ("name", ma.fields.String),
            ("symbol", ma.fields.String),
        ],
    )
    def test_field_is_expected_type(self, field, field_type):
        assert type(ConstructorArgsSchema._declared_fields[field]) == field_type


class TestContractSchema:
    @pytest.mark.parametrize("field", ["name", "address"])
    def test_field_is_required(self, field):
        assert ContractSchema._declared_fields[field].required is True

    @pytest.mark.parametrize(
        "field, field_type", [("name", ma.fields.String), ("address", ma.fields.String)]
    )
    def test_field_is_expected_type(self, field, field_type):
        assert type(ContractSchema._declared_fields[field]) == field_type


@pytest.mark.parametrize(
    "schema",
    argvalues=[TokenCreateSchema(), TokenMintSchema()],
    ids=["TokenCreateSchema", "TokenMintSchema"],
)
class TestSchemaDefinition:
    def test_schema_inherits_from_rpccreateresourceschema(self, schema):
        assert isinstance(schema, RPCCreateResourceSchema)


class TestTokenCreateSchema:
    @pytest.mark.parametrize("field", ["token_name", "constructor_args"])
    def test_deserializer_field_is_load_only(self, field):
        assert TokenCreateSchema._declared_fields[field].load_only is True

    @pytest.mark.parametrize("field", argvalues=["contract", "deployment_block"])
    def test_serializer_field_is_dump_only(self, field):
        assert TokenCreateSchema._declared_fields[field].dump_only is True

    @pytest.mark.parametrize(
        "field, field_type",
        argvalues=[("constructor_args", ma.fields.Nested), ("token_name", ma.fields.String)],
    )
    def test_deserializer_fields_are_expected_type(self, field, field_type):
        assert type(TokenCreateSchema._declared_fields[field]) == field_type

    @pytest.mark.parametrize(
        "field, field_type",
        argvalues=[("contract", ma.fields.Nested), ("deployment_block", ma.fields.Integer)],
    )
    def test_serializer_fields_are_expected_type(self, field, field_type):
        assert type(TokenCreateSchema._declared_fields[field]) == field_type

    @pytest.mark.parametrize(
        "field", argvalues=["constructor_args", "contract", "deployment_block"]
    )
    def test_field_is_required(self, field):
        assert TokenCreateSchema._declared_fields[field].required is True

    def test_token_name_field_is_optional(self):
        assert TokenCreateSchema._declared_fields["token_name"].required is False

    @pytest.mark.parametrize(
        "field, schema",
        argvalues=[("constructor_args", ConstructorArgsSchema), ("contract", ContractSchema)],
    )
    def test_field_nests_correct_schema(self, field, schema):
        assert TokenCreateSchema._declared_fields[field].nested == schema


class TestTokenMintSchema:
    @pytest.mark.parametrize(
        "field", ["target_address", "contract_address", "amount", "gas_limit"]
    )
    def test_field_is_load_only(self, field):
        assert TokenMintSchema._declared_fields[field].load_only is True

    @pytest.mark.parametrize("field", ["tx_hash"])
    def test_field_is_dump_only(self, field):
        assert TokenMintSchema._declared_fields[field].dump_only is True

    @pytest.mark.parametrize(
        "field, field_type",
        argvalues=[
            ("target_address", ma.fields.String),
            ("contract_address", ma.fields.String),
            ("gas_limit", ma.fields.Integer),
            ("amount", ma.fields.Integer),
        ],
    )
    def test_deserializer_fields_are_expected_type(self, field, field_type):
        assert type(TokenMintSchema._declared_fields[field]) == field_type

    @pytest.mark.parametrize("field, field_type", argvalues=[("tx_hash", BytesField)])
    def test_serializer_fields_are_expected_type(self, field, field_type):
        assert type(TokenMintSchema._declared_fields[field]) == field_type

    @pytest.mark.parametrize(
        "field", argvalues=["target_address", "contract_address", "amount", "gas_limit", "tx_hash"]
    )
    def test_field_is_required(self, field):
        assert TokenMintSchema._declared_fields[field].required is True
