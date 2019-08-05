import marshmallow as ma
import pytest

from scenario_player.services.common.schemas import BytesField
from scenario_player.services.rpc.schemas.base import RPCClientID, RPCCreateResourceSchema
from scenario_player.services.rpc.schemas.instances import (
    DeleteInstanceRequest,
    GasPrice,
    NewInstanceRequest,
)


@pytest.mark.parametrize(
    "value, expected",
    argvalues=[
        ("fast", "FAST"),
        ("MEDIUM", "MEDIUM"),
        ("MeDiUm", "MEDIUM"),
        ("4", 4),
        (4, ma.ValidationError),
        ("super-fast", ma.ValidationError),
        (1.5, ma.ValidationError),
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
def test_gas_price_field_deserialize_returns_correctly(value, expected):
    """We expect the GasPrice field to deserialize the input correctly, following
    these rules:

        * the value must be either a string
        * If it can be deserialized to an `integer`, it's returned as such.
        * If the string is a **known** gas-price-strategy name, it is upper-cased and returned.
        * In all other cases, a ValidationError is raised.
    """
    if expected != ma.ValidationError:
        assert GasPrice()._deserialize(value, "gas_price", {}) == expected
    else:
        with pytest.raises(expected):
            GasPrice()._deserialize(value, "gas_price", {})


class TestNewInstanceReuqest:
    @pytest.mark.parametrize(
        "field, cls",
        argvalues=[
            ("chain_url", ma.fields.Url),
            ("privkey", BytesField),
            ("gas_price", GasPrice),
            ("client_id", RPCClientID),
        ],
        ids=[
            "`chain_url` is a URL field",
            "`privkey` is a BytesField field",
            "`gas_price` is a GasPrice field",
            "`client_id` is a RPCClientID field",
        ],
    )
    def test_fields_are_instances_of_correct_types(self, field, cls):
        schema_fields = NewInstanceRequest()._declared_fields
        assert isinstance(schema_fields[field], cls)

    @pytest.mark.parametrize("field", argvalues=["chain_url", "privkey", "gas_price"])
    def test_field_is_load_only(self, field):
        schema_fields = NewInstanceRequest()._declared_fields
        assert schema_fields[field].load_only is True

    def test_client_id_field_is_dump_only(self):
        schema_fields = NewInstanceRequest()._declared_fields
        assert schema_fields["client_id"].dump_only is True

    @pytest.mark.parametrize("field", argvalues=["chain_url", "privkey", "client_id"])
    def test_required_fields_have_their_required_attr_set_to_true(self, field):
        schema_fields = NewInstanceRequest()._declared_fields
        assert schema_fields[field].required is True

    def test_optional_gas_price_field_has_its_missing_value_set(self):
        schema_fields = NewInstanceRequest()._declared_fields
        assert schema_fields["gas_price"].missing == "FAST"


def test_delete_instance_request_schema_inherits_from_rpc_create_resource_schema():
    """We do not need any additional fields for the request, aside the client_id field.

    This field is load_only by default, which is also exactly what we need.
    """
    assert issubclass(DeleteInstanceRequest, RPCCreateResourceSchema)
