"""Request a new JSONRPCClient for a given private key and test net.

The blueprint offers endpoints to request an instance, as well as deleting one.

The following endpoints are supplied by this blueprint:

    * [POST] /rpc/client
        Return a new JSONRPCClient instance id. If an instance already exists for
        the given private key and test network, we return that instance instead.

    * [DELETE] /rpc/client?client_id=<str>
        Delete the JSONRPCClient instance with the given ID. This pops the
        instance from the application's RPCRegistry, handing it over to garbage
        collection.

"""
from flask import Blueprint, Response, abort, current_app, jsonify, request

from scenario_player.constants import GAS_STRATEGIES
from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.rpc.schemas.instances import (
    DeleteInstanceRequest,
    NewInstanceRequest,
)

instances_blueprint = Blueprint("instances_blueprint", __name__)
new_instance_schema = NewInstanceRequest()
delete_instance_schema = DeleteInstanceRequest()


@instances_blueprint.route("/rpc/client", methods=["POST"])
def rpc_create_view():
    """Request a client id for a JSONRPCClient instance with the given configuration.

    This view is idempotent, and will return an exising instance if one with
    an identical configuration already exists.

    FIXME: calling new_instance_schema.jsonify() results in a look-up error
        when calling it with the newly created RPC client's ID.

    ---
    post:
      description: "Create and send a new transaction via RPC."
      parameters:
      - name: chain_url
        required: true
        in: query
        schema:
          type: string

      - name: privkey
        required: true
        in: query
        schema:
          type: str

      - name: gas_price
        required: false
        in: query
        schema:
          type: str

      responses:
        200:
          description: "The client id of the created/existing RPC instance matching your config."
          content:
            application/json:
              schema: {$ref: '#/components/schemas/NewInstanceRequest'}
    """
    handlers = {"POST": create_client}
    with REDMetricsTracker():
        return handlers[request.method]()


def create_client():
    data = new_instance_schema.validate_and_deserialize(request.form)

    gas_price = data.get("gas_price", "FAST")

    if isinstance(gas_price, int):

        def fixed_gas_price(*_, **__):
            return gas_price

        strategy_callable = fixed_gas_price
    else:
        try:
            strategy_callable = GAS_STRATEGIES[gas_price]
        except KeyError:
            return abort(400, f'Invalid gas_price value: "{gas_price}"')

    chain_url, privkey = data["chain_url"], data["privkey"]

    client = current_app.config["rpc-client"][(chain_url, privkey, strategy_callable)]

    return jsonify({"client_id": client.client_id})


@instances_blueprint.route("/rpc/client", methods=["DELETE"])
def rpc_delete_view():
    """Delete the JSONRPCCLient instance with the given `client_id`.

    This method always return 204, even if the client_id did not exist.

    ---
    delete:
      description: "Assign the instance related to `client_id` for deletion."
      parameters:
      - name: client_id
        required: true
        in: query
        schema:
          type: string

      responses:
        204:
          description: >
            The entry for the client was deleted, and the instance
            handed over to garbage collection.
          content:
            application/json:
              schema: {$ref: '#/components/schemas/DeleteInstanceRequest'}
    """
    handlers = {"DELETE": delete_client}
    with REDMetricsTracker():
        return handlers[request.method]()


def delete_client(client_id):
    delete_instance_schema.validate_and_deserialize({"client_id": request.params["client_id"]})
    current_app.config["rpc-client"].pop(client_id, None)
    return Response(204)
