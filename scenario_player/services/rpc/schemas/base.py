from flask import current_app
from marshmallow.fields import String

from raiden.network.rpc.client import JSONRPCClient
from scenario_player.services.common.schemas import SPSchema


class RPCClientID(String):
    """A field for (de)serializing a :class:`raiden.network.rpc.client.JSONRPCClient` instance
    from and to a client id given as a :class:`str`."""

    default_error_messages = {
        "unknown_client_id": "Could not find an RPC Client with a matching client id!",
        "missing_client_id": "Could not fetch a client id from the config for RPC client!",
        "empty": "Must not be empty!",
    }

    def __init__(self, *args, **kwargs):
        super(RPCClientID, self).__init__(*args, **kwargs)

    def _deserialize(self, value: str, attr, data, **kwargs) -> JSONRPCClient:
        """Load the :class:`JSONRPCClient` object related to the given `client_id` str.

        If `kwargs` is not empty, we will emit a warning, since we do not currently
        support additional kwargs passed to this method.

        """
        if not value:
            self.fail("empty")

        deserialized_string = super(RPCClientID, self)._deserialize(value, attr, data, **kwargs)

        try:
            client, _ = current_app.config["rpc-client"][deserialized_string]
        except KeyError:
            self.fail("unknown_client_id")

        return client

    def _serialize(self, value: JSONRPCClient, attr, obj, **kwargs) -> str:
        """Prepare :class:`JSONRPCClient` object for JSON-encoding.

        Returns the object's related client id from the config of the flask app.
        """
        for client_id, client in current_app.config["rpc-client"].items():
            client, _ = client
            if client == value:
                return client_id
        self.fail("missing_client_id")


class RPCCreateResourceSchema(SPSchema):
    client_id = RPCClientID(required=True)
