"""Send and track a transaction via JSONRPC.

The blueprint offers endpoints to send a transaction, as well
as tracking one or more transactions by their hashes.

The following endpoints are supplied by this blueprint:

    * [POST, GET] /transactions
        Request the status of one or more transactions using their hashes, or
        create a new transaction. The parameters for the latter must be supplied as
        form data.

"""
from flask import Blueprint, Response, request, current_app

from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.rpc.schemas.transactions import TransactionSendRequest


transactions_blueprint = Blueprint("transactions_view", __name__)


transaction_send_schema = TransactionSendRequest()


@transactions_blueprint.route("/rpc/client/<rpc_client_id>/transactions", methods=["POST"])
def transactions_route(rpc_client_id):
    handlers = {"POST": new_transaction}
    with REDMetricsTracker():
        return handlers[request.method](rpc_client_id)


def new_transaction(rpc_client_id):
    """Create a new transaction.

    The given parameters will be passed to the service's
    :class:`raiden.network.rpc.client.JSONRPCClient` instance, which will then
    execute the transaction.

    The resulting transaction hash will be returned to the requester.

    Example::

        POST /rpc/client/<rpc_client_id>/transactions

            {
                "to": <str>,
                "startgas": <number>,
                "value": <number>,
            }

        200 OK

            {
                "tx_hash": <str>,
            }

    """
    data = transaction_send_schema.validate_and_deserialize(request.form)

    # Get the services JSONRPCClient from the flask app's app_context.
    rpc_client, _ = current_app.config["rpc-client"][rpc_client_id]

    result = rpc_client.send_transaction(**data)

    return Response(transaction_send_schema.dumps({"tx_hash": result}).encode("UTF-8"), status=200)
