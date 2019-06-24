from flask import Blueprint, abort

from scenario_player.services.common.metrics import REDMetricsTracker

transactions_view = Blueprint("transactions_view", __name__)


@transactions_view.route("/transactions", methods=["POST", "GET"])
def transactions_route():
    handlers = {"GET": get_transaction_status, "POST": new_transaction}
    with REDMetricsTracker(request.method, "/transactions"):
        handlers[request.method]()


def new_transaction():
    """Create a new transaction.

    Example::

        POST /transactions

            {
                "to": <ACCOUNT_ADDRESS>,
                "start_gas": <float>,
                "value": <float>,
            }

        200 OK

            {
                TODO: What should the response look like?
            }
    """
    to_address = request.form["to"]
    start_gas = request.form["start_gas"]
    value = request.form["value"]
    abort(501)


def get_transaction_status():
    """Return a list of transaction objects by a list of `hashes`.

    Example::

        GET /transactions?hashes=<str>,<str>,<str>

        200 OK

            {
                "transactions": [],
            }

        408 Request Timeout

            {
                "error": "Exceeded timeout for transaction lookup request!"
                "missing": [],
                "found": [],
            }

    """
    hashes = request.args["hashes"]
    abort(501)
