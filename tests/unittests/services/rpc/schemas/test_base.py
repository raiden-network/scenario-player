from unittest.mock import Mock

import pytest
from flask import current_app
from werkzeug.exceptions import BadRequest

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


def test_rpcclientid_deserializes_to_rpc_client_instance(
    test_schema, rpc_service_app, rpc_client_id
):
    """:meth:`RPCClientID._deserialize` is expected to return a :class:`JSONRPCClient` object."""
    client_id_field = RPCClientID()
    client_id = rpc_client_id
    expected = (object(), client_id)

    with rpc_service_app.app_context():
        current_app.config["rpc-client"].dict[client_id] = expected
        assert client_id_field._deserialize(client_id, "client_id", {}) == expected


def test_rpcclientid_serializes_to_string(test_schema, rpc_service_app, rpc_client_id):
    """:meth:`RPCClientID._serialize` is expected to return a :class:`str` object."""
    client_id = RPCClientID()
    instance = object()
    expected_id = rpc_client_id

    with rpc_service_app.app_context():
        current_app.config["rpc-client"].dict[expected_id] = instance
        assert client_id._serialize(instance, "client_id", {}) == expected_id  # type: ignore


@pytest.mark.parametrize(
    "input_dict, exception",
    argvalues=[
        ({"client_id": "my_client"}, False),
        ({"client_id": "my_client_2"}, BadRequest),
        ({}, BadRequest),
    ],
    ids=[
        "Existing Client ID passed succeeds",
        "Non-existing Client ID fails",
        "Missing Client ID fails",
    ],
)
def test_rpccreateresourceschema_validate_and_serialize_raises_bad_request_on_invalid_client_id(
    input_dict, exception, test_schema, rpc_service_app, rpc_client_id
):
    client_id = "kjhgfds"
    if not exception:
        # inject a valid, existing uuid4 as client id.
        input_dict["client_id"] = rpc_client_id

    with rpc_service_app.app_context():
        current_app.config["rpc-client"].dict[client_id] = object()
        if exception:
            with pytest.raises(exception):
                test_schema.validate_and_deserialize(input_dict)
        else:
            test_schema.validate_and_deserialize(input_dict)


def test_rpccreateresourceschema_validate_and_deserialize_adds_client_key_to_unpacked_value(
    test_schema, rpc_service_app, rpc_client_id
):
    client_id = rpc_client_id
    expected_instance = Mock(client_id=client_id)
    input_dict = {"client_id": client_id}
    expected = {"client_id": client_id, "client": expected_instance}
    with rpc_service_app.app_context():
        current_app.config["rpc-client"].dict[client_id] = expected_instance
        assert test_schema.validate_and_deserialize(input_dict) == expected
