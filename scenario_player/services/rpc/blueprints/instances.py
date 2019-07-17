"""Request a new JSONRPCClient for a given private key and test net.from marshmallow.fields import Float, List, String, Url

The blueprint offers endpoints to request an instance, as well as deleting one.

The following endpoints are supplied by this blueprint:

    * [POST] /rpc/client
        Return a new JSONRPCClient instance id. If an instance already exists for
        the given private key and test network, we return that instance instead.

    * [DELETE] /rpc/client/<rpc_client_id>
        Delete the JSONRPCClient instance with the given ID. This closes the
        object and pops it from the application's RPCRegistry.

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
                "rpc_client_id": <str>,
            }

    """
    data = new_instance_schema.validate_and_deserialize(request.form)
    privkey, chain_url = data["privkey"], data["chain_url"]
    gas_price_strategy = data["gas_price_strategy"]
    _, rpc_client_id = current_app.config["rpc-client"][(chain_url, privkey, gas_price_strategy)]
    resp_data = new_instance_schema.dumps({"rpc_client_id": rpc_client_id})
    return jsonify(resp_data)


@instances_blueprint.route("/rpc/client/<rpc_client_id>", methods=["DELETE"])
def rpc_delete_view(rpc_client_id):
    """Delete the JSONRPCCLient instance with the given `rpc_client_id`.

    This method always return 204, even if the rpc_client_id did not exist.

    Example::

        DELETE /rpc/client/valid_rpc_client_id

        204 No Content


        DELETE /rpc/client/non_existing_rpc_client_id

        204 No Content

    """
    handlers = {"DELETE": delete_client}
    with REDMetricsTracker():
        return handlers[request.method](rpc_client_id)


def delete_client(rpc_client_id):
    delete_instance_schema.validate_and_deserialize({"rpc_client_id": rpc_client_id})
    current_app.config["rpc-client"].pop(rpc_client_id, None)
    return Response(204)
