"""Send and track a transaction via JSONRPC.

The blueprint offers endpoints to send a transaction, as well
as tracking one or more transactions by their hashes.

The following endpoints are supplied by this blueprint:

    * [POST] /transactions
        Request the status of one or more transactions using their hashes, or
        create a new transaction. The parameters for the latter must be supplied as
        form data.

"""
from flask import Blueprint, request
from structlog import get_logger

from raiden.network.rpc.client import EthTransfer
from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.rpc.schemas.transactions import SendTransactionSchema
from scenario_player.services.rpc.utils import RPCClient

log = get_logger(__name__)


transactions_blueprint = Blueprint("transactions_view", __name__)


transaction_send_schema = SendTransactionSchema()


@transactions_blueprint.route("/rpc/transactions", methods=["POST"])
def transactions_route():
    """Create a new transaction.

    The given parameters will be passed to the service's
    :class:`raiden.network.rpc.client.JSONRPCClient` instance, which will then
    execute the transaction.

    The resulting transaction hash will be returned to the requester.
    ---
    parameters:
      - name: client_id
        required: true
        in: query
        schema:
          type: string
    post:
      description: "Create and send a new transaction via RPC."
      parameters:
      - name: to
        required: true
        in: query
        schema:
          type: string

      - name: start_gas
        required: true
        in: query
        schema:
          type: number
          format: double

      - name: value
        required: true
        in: query
        schema:
          type: number
          format: double

      responses:
        200:
          description: "Address and deployment block of the deployed contract."
          content:
            application/json:
              schema: {$ref: '#/components/schemas/SendTransactionSchema'}
    """
    handlers = {"POST": new_transaction}
    with REDMetricsTracker():
        return handlers[request.method]()


def new_transaction():
    data = transaction_send_schema.validate_and_deserialize(request.get_json())
    rpc_client: RPCClient = data.pop("client")

    log.debug("Performing transaction", params=data)
    result = rpc_client.transact(
        EthTransfer(
            to_address=data["to"], value=data["value"], gas_price=rpc_client.web3.eth.gasPrice
        )
    )

    return transaction_send_schema.jsonify({"tx_hash": result})
