"""Send and track a transaction via JSONRPC.

The blueprint offers endpoints to send a transaction, as well
as tracking one or more transactions by their hashes.

The following endpoints are supplied by this blueprint:

    * [POST, GET] /transactions
        Request the status of one or more transactions using their hashes, or
        create a new transaction. The parameters for the latter must be supplied as
        form data.

"""
from flask import Blueprint, Response, request

from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.rpc.schemas.transactions import TransactionSendRequest

transactions_blueprint = Blueprint("transactions_view", __name__)


transaction_send_schema = TransactionSendRequest()


@transactions_blueprint.route("/rpc/client/transactions", methods=["POST"])
def transactions_route():
    handlers = {"POST": new_transaction}
    with REDMetricsTracker():
        return handlers[request.method]()


def new_transaction():
    """Create a new transaction.

    The given parameters will be passed to the service's
    :class:`raiden.network.rpc.client.JSONRPCClient` instance, which will then
    execute the transaction.

    The resulting transaction hash will be returned to the requester.

    Example::

        POST /rpc/client/transactions

            {
                "client": <str>,
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
    rpc_client = data["client_id"]

    result = rpc_client.send_transaction(**data)

    return Response(transaction_send_schema.dumps({"tx_hash": result}).encode("UTF-8"), status=200)
