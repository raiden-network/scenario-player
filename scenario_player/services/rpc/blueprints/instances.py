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
from flask import Blueprint, Response, current_app, jsonify, request

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
    handlers = {"POST": create_client}
    with REDMetricsTracker():
        return handlers[request.method]()


def create_client():
    """Request a JSONRPCClient instance for the given configuration.

    This view is idempotent, and will return an exising instance if one with
    an identical configuration already exists.

    Example::

        POST /rpc/client

            {
                "chain_url": <str>,
                "privkey": <str>,
                "gas_price_strategy": <str - optional>,
            }

        200 OK

            {
                "client_id": <str>,
            }

    """
    data = new_instance_schema.validate_and_deserialize(request.form)
    privkey, chain_url = data["privkey"], data["chain_url"]
    gas_price_strategy = data["gas_price_strategy"]
    _, client_id = current_app.config["rpc-client"][(chain_url, privkey, gas_price_strategy)]
    resp_data = new_instance_schema.dumps({"client_id": client_id})
    return jsonify(resp_data)


@instances_blueprint.route("/rpc/client", methods=["DELETE"])
def rpc_delete_view():
    """Delete the JSONRPCCLient instance with the given `client_id`.

    This method always return 204, even if the client_id did not exist.

    Example::

        DELETE /rpc/client?client_id=valid_client_id

        204 No Content


        DELETE /rpc/client?client_id=non_existing_client_id

        204 No Content

    """
    handlers = {"DELETE": delete_client}
    with REDMetricsTracker():
        return handlers[request.method]()


def delete_client(client_id):
    delete_instance_schema.validate_and_deserialize({"client_id": request.params["client_id"]})
    current_app.config["rpc-client"].pop(client_id, None)
    return Response(204)
