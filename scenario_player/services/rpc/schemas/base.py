from typing import Tuple

from flask import current_app
from marshmallow.fields import String

from raiden.network.rpc.client import JSONRPCClient
from scenario_player.services.common.schemas import SPSchema


class RPCClientID(String):
    """A field for (de)serializing a :class:`raiden.network.rpc.client.JSONRPCClient` instance
    from and to a client id given as a :class:`str`.

    The string must be a valid hexadecimal string.
    """

    default_error_messages = {
        "unknown_client_id": "Could not find an RPC Client with a matching client id!",
        "missing_client_id": "Could not fetch a client id from the config for RPC client!",
        "empty": "Must not be empty!",
        "not_hex": "Client ID must be a hexadecimal string!",
    }

    def __init__(self, *args, **kwargs):
        super(RPCClientID, self).__init__(*args, **kwargs)

    def _deserialize(self, value: str, attr, data, **kwargs) -> Tuple[JSONRPCClient, str]:
        """Load the :class:`JSONRPCClient` object related to the given `client_id` str.

        If `kwargs` is not empty, we will emit a warning, since we do not currently
        support additional kwargs passed to this method.

        """
        if not value:
            self.fail("empty")

        deserialized_string = super(RPCClientID, self)._deserialize(value, attr, data, **kwargs)

        try:
            int(deserialized_string, 16)
        except ValueError:
            self.fail("not_hex")

        try:
            client, client_id = current_app.config["rpc-client"][deserialized_string]
        except KeyError:
            self.fail("unknown_client_id")

        return client, client_id

    def _serialize(self, value: JSONRPCClient, attr, obj, **kwargs) -> str:
        """Prepare :class:`JSONRPCClient` object for JSON-encoding.

        Returns the object's related client id from the config of the flask app.
        """
        for client_id, client_tuple in current_app.config["rpc-client"].items():
            client, _ = client_tuple
            if client == value:
                return client_id
        self.fail("missing_client_id")


class RPCCreateResourceSchema(SPSchema):
    """Default Schema for POST Methods to the RPC client.

    Expects a `client_id` to be present in :var`flask.request.form`. When
    calling :class:`.validate_and_deserialize`, the class instance will dynamically
    load the related RPC client instance and add it to the returned data under the
    `client` key.

    parameters:

        - client_id (:class:`.RPCClientID`)

    """

    client_id = RPCClientID(required=True, load_only=True)

    def validate_and_deserialize(self, data_obj) -> dict:
        deserialized = super(RPCCreateResourceSchema, self).validate_and_deserialize(data_obj)
        client, client_id = deserialized["client_id"]
        deserialized["client_id"], deserialized["client"] = client_id, client
        return deserialized
