"""Schema Test cases for the RPC service.

REFAC: The test cases asserting correctness of fields can be refactored.
"""
import pytest
from marshmallow.exceptions import ValidationError
from marshmallow.fields import Integer, Nested, String, Url

from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.blueprints.transactions import SendTransactionSchema
from scenario_player.services.rpc.schemas.base import RPCClientID, RPCCreateResourceSchema
from scenario_player.services.rpc.schemas.instances import (
    CreateClientSchema,
    DeleteInstanceRequest,
    GasPrice,
)
from scenario_player.services.rpc.schemas.tokens import (
    ConstructorArgsSchema,
    ContractSchema,
    ContractTransactSchema,
    TokenCreateSchema,
)


class TestGasPriceField:
    @pytest.mark.parametrize(
        "value, expected",
        argvalues=[
            ("fast", "FAST"),
            ("MEDIUM", "MEDIUM"),
            ("MeDiUm", "MEDIUM"),
            ("4", 4),
            (4, ValidationError),
            ("super-fast", ValidationError),
            (1.5, ValidationError),
        ],
        ids=[
            "Passing known lower-case strategy succeeds",
            "Passing known upper-case strategy succeeds",
            "Passing known mixed-case strategy succeeds",
            "Passing an int as a string succeeds",
            "Passing an int fails",
            "Passing an unknown gas strategy fails",
            "Passing a float fails",
        ],
    )
    def test_gas_price_field_deserialize_returns_correctly(self, value, expected):
        """We expect the GasPrice field to deserialize the input correctly, following
        these rules:

            * the value must be either a string
            * If it can be deserialized to an `integer`, it's returned as such.
            * If the string is a **known** gas-price-strategy name, it is upper-cased and returned.
            * In all other cases, a ValidationError is raised.
        """
        if expected != ValidationError:
            assert GasPrice()._deserialize(value, "gas_price", {}) == expected
        else:
            with pytest.raises(expected):
                GasPrice()._deserialize(value, "gas_price", {})


class TestConstructorArgsSchema:
    @pytest.mark.parametrize("field", ["decimals", "name", "symbol"])
    def test_field_is_required(self, field):
        assert ConstructorArgsSchema._declared_fields[field].required is True

    @pytest.mark.parametrize(
        "field, field_type", [("decimals", Integer), ("name", String), ("symbol", String)]
    )
    def test_field_is_expected_type(self, field, field_type):
        assert type(ConstructorArgsSchema._declared_fields[field]) == field_type


class TestContractSchema:
    @pytest.mark.parametrize("field", ["name", "address"])
    def test_field_is_required(self, field):
        assert ContractSchema._declared_fields[field].required is True

    @pytest.mark.parametrize("field, field_type", [("name", String), ("address", String)])
    def test_field_is_expected_type(self, field, field_type):
        assert type(ContractSchema._declared_fields[field]) == field_type


@pytest.mark.parametrize(
    "schema", argvalues=[TokenCreateSchema(), ContractTransactSchema(), DeleteInstanceRequest()]
)
def test_schema_inherits_from_rpccreateresourceschema(schema):
    assert isinstance(schema, RPCCreateResourceSchema)


class TestSendTransactionSchema:
    @pytest.fixture(autouse=True)
    def setup_schema_tests(self):
        self.declared_fields = SendTransactionSchema._declared_fields

    @pytest.mark.parametrize("field", argvalues=["to", "startgas", "value", "tx_hash"])
    def test_field_is_required(self, field):
        assert self.declared_fields[field].required is True

    @pytest.mark.parametrize("field", argvalues=["to", "startgas", "value"])
    def test_serializer_field_is_load_only(self, field):
        assert self.declared_fields[field].load_only is True

    @pytest.mark.parametrize("field", argvalues=["tx_hash"])
    def test_deserializer_field_is_dump_only(self, field):
        assert self.declared_fields[field].dump_only is True

    @pytest.mark.parametrize(
        "field, field_type",
        argvalues=[
            ("to", String),
            ("startgas", Integer),
            ("value", Integer),
            ("tx_hash", BytesField),
        ],
    )
    def test_field_is_expected_type(self, field, field_type):
        assert type(self.declared_fields[field]) == field_type


class TestTokenCreateSchema:
    @pytest.fixture(autouse=True)
    def setup_schema_tests(self):
        self.declared_fields = TokenCreateSchema._declared_fields

    @pytest.mark.parametrize("field", ["token_name", "constructor_args"])
    def test_deserializer_field_is_load_only(self, field):
        assert self.declared_fields[field].load_only is True

    @pytest.mark.parametrize("field", argvalues=["contract", "deployment_block"])
    def test_serializer_field_is_dump_only(self, field):
        assert self.declared_fields[field].dump_only is True

    @pytest.mark.parametrize(
        "field, field_type",
        argvalues=[
            ("constructor_args", Nested),
            ("token_name", String),
            ("contract", Nested),
            ("deployment_block", Integer),
        ],
    )
    def test_field_is_expected_type(self, field, field_type):
        assert type(self.declared_fields[field]) == field_type

    @pytest.mark.parametrize(
        "field", argvalues=["constructor_args", "contract", "deployment_block"]
    )
    def test_field_is_required(self, field):
        assert self.declared_fields[field].required is True

    @pytest.mark.parametrize("field", ["token_name"])
    def test_field_is_optional(self, field):
        assert self.declared_fields[field].required is False

    @pytest.mark.parametrize(
        "field, schema",
        argvalues=[("constructor_args", ConstructorArgsSchema), ("contract", ContractSchema)],
    )
    def test_field_nests_correct_schema(self, field, schema):
        assert self.declared_fields[field].nested == schema


class TestContractTransactSchema:
    @pytest.fixture(autouse=True)
    def setup_schema_tests(self):
        self.declared_fields = ContractTransactSchema._declared_fields

    @pytest.mark.parametrize(
        "field", ["target_address", "contract_address", "amount", "gas_limit"]
    )
    def test_deserializer_field_is_load_only(self, field):
        assert self.declared_fields[field].load_only is True

    @pytest.mark.parametrize("field", ["tx_hash"])
    def test_serializer_field_is_dump_only(self, field):
        assert self.declared_fields[field].dump_only is True

    @pytest.mark.parametrize(
        "field, field_type",
        argvalues=[
            ("target_address", String),
            ("contract_address", String),
            ("gas_limit", Integer),
            ("amount", Integer),
            ("tx_hash", BytesField),
        ],
    )
    def test_field_is_expected_type(self, field, field_type):
        assert type(self.declared_fields[field]) == field_type

    @pytest.mark.parametrize(
        "field", argvalues=["target_address", "contract_address", "amount", "gas_limit", "tx_hash"]
    )
    def test_field_is_required(self, field):
        assert self.declared_fields[field].required is True


class TestNewInstanceReuqest:
    @pytest.fixture(autouse=True)
    def setup_schema_tests(self):
        self.declared_fields = CreateClientSchema._declared_fields

    @pytest.mark.parametrize(
        "field, field_type",
        argvalues=[
            ("chain_url", Url),
            ("privkey", BytesField),
            ("gas_price", GasPrice),
            ("client_id", RPCClientID),
        ],
    )
    def test_field_is_expected_type(self, field, field_type):
        assert type(self.declared_fields[field]) == field_type

    @pytest.mark.parametrize("field", argvalues=["chain_url", "privkey", "gas_price"])
    def test_field_is_load_only(self, field):
        assert self.declared_fields[field].load_only is True

    @pytest.mark.parametrize("field", argvalues=["client_id"])
    def test_field_is_dump_only(self, field):
        assert self.declared_fields[field].dump_only is True

    @pytest.mark.parametrize("field", argvalues=["chain_url", "privkey", "client_id"])
    def test_required_fields_have_their_required_attr_set_to_true(self, field):
        assert self.declared_fields[field].required is True

    @pytest.mark.parametrize("field, missing", argvalues=[("gas_price", "FAST")])
    def test_optionalfield_has_its_missing_value_set(self, field, missing):
        assert self.declared_fields[field].missing == missing
