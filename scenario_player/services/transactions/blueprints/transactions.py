"""Send and track a transaction via JSONRPC.

The blueprint offers endpoints to send a transaction, as well
as tracking one or more transactions by their hashes.

The following endpoints are supplied by this blueprint:

    * [POST, GET] /transactions
        Request the status of one or more transactions using their hashes, or
        create a new transaction. The parameters for the latter must be supplied as
        form data.

"""
from flask import Blueprint, abort

from raiden.network.rpc.client import JSONRPCClient

from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.transactions.schemas.transactions import (
    TransactionSendRequest,
    TransactionSendResponse,
)


transactions_blueprint = Blueprint("transactions_view", __name__)


@transactions_blueprint.route("/transactions", methods=["POST"])
def transactions_route():
    handlers = {"POST": new_transaction}
    with REDMetricsTracker(request.method, "/transactions"):
        return handlers[request.method]()


def new_transaction():
    """Create a new transaction.

    The given parameters will be passed to the service's :class:`raiden.network.rpc.client.JSONRPCClient`
    instance, which will then execute the transaction.

    The resulting transaction hash will be returned to the requester.

    Example::

        POST /transactions

            {
                "to": <str>,
                "start_gas": <number>,
                "value": <number>,
            }

        200 OK

            {
                "tx_hash": <bytes>,
            }

    """
    data = TransactionSendRequest().validate_and_serialize(request.form)

    # Get the services JSONRPCClient from the flask app's app_context (`g`).
    try:
        rpc_client = g.config['rpc-client']
        if not isinstance(rpc_client, JSONRPCClient):
            raise RuntimeError
    except (RuntimeError, KeyError):
        abort(500, "No JSONRPCClient instance available on service!")
    result = rpc_client.send_transaction(**data)

    return TransactionSendResponse().dump({"tx_hash": result})

