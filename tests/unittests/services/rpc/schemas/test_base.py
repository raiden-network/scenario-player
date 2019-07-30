import pytest
from flask import current_app
from werkzeug.exceptions import BadRequest, NotFound

from scenario_player.services.rpc.schemas.base import RPCClientID, RPCCreateResourceSchema


@pytest.fixture
def test_schema():
    """Minimal schema to test the :class:`RPCCreateResourceSchema` and :class:`RPCClientID` classes.

    Defines a single :class:`RPCClientID` at :attr:`.TestSchema.client_id` on the
    sub-class of :class:`RPCCreateResourceSchema`.

    The sub-class is called :class:`TestSchema`.

    An instance of this sub-class is returned.
    """

    class TestSchema(RPCCreateResourceSchema):
        client_id = RPCClientID(required=True)

    return TestSchema()


def test_rpcclientid_deserializes_to_rpc_client_instance(test_schema, transaction_service_app):
    """:meth:`RPCClientID._deserialize` is expected to return a :class:`JSONRPCClient` object."""
    client_id = RPCClientID()
    expected = object()
    input_string = "my_client_id"

    with transaction_service_app.app_context() as app:
        current_app.config["rpc-client"].dict[input_string] = expected
        assert client_id._deserialize(input_string, "client_id", {}) == expected


def test_rpcclientid_serializes_to_string(test_schema, transaction_service_app):
    """:meth:`RPCClientID._serialize` is expected to return a :class:`str` object."""

    client_id = RPCClientID()
    instance = object()
    expected_id = "the_client_id"

    with transaction_service_app.app_context() as app:
        current_app.config["rpc-client"].dict[expected_id] = instance
        assert client_id._serialize(instance, "client_id", {}) == expected_id


@pytest.mark.parametrize(
    "input_dict, exception",
    argvalues=[
        ({"client_id": "my_client"}, False),
        ({"client_id": "my_client_2"}, NotFound),
        ({}, BadRequest),
    ],
    ids=[
        "Existing Client ID passed succeeds",
        "Non-existing Client ID fails",
        "Missing Client ID fails",
    ],
)
def test_rpccreateresourceschema_validate_and_serialize_raises_bad_request_on_invalid_client_id(
    input_dict, exception, test_schema, transaction_service_app
):

    with transaction_service_app.app_context() as app:
        current_app.config["rpc-client"].dict["my_client"] = object()
        if exception:
            with pytest.raises(exception):
                test_schema.validate_and_deserialize(input_dict)
        else:
            test_schema.validate_and_deserialize(input_dict)
