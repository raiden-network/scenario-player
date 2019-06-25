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

from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.transactions.schemas.transactions import (
    TransactionSendRequest,
    TransactionSendResponse,
    TransactionTrackRequest,
    TransactionTrackResponse,
)


transactions_view = Blueprint("transactions_view", __name__)


@transactions_view.route("/transactions", methods=["POST", "GET"])
def transactions_route():
    handlers = {"GET": get_transaction_status, "POST": new_transaction}
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
    abort(501)
    return TransactionSendResponse().dump(data)


def get_transaction_status():
    """Return a list of transaction objects by a list of `hashes`.

    Example::

        GET /transactions?hashes=<str>,<str>,<str>

        200 OK

            {
                "transactions": [<tx_hash>, ...],
            }

        408 Request Timeout

            {
                "missing": [<tx_hash>, ...],
                # If any transactions have been found before the
                # request timed out, they will be listed here.
                "found": [<tx_hash>, ...],
            }

    """
    data = TransactionTrackRequest().validate_and_serialize(reuqest.form)
    abort(501)
    return TransactionTrackResponse().dump(data)
