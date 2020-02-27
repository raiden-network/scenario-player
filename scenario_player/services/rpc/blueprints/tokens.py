"""Create, query and mint tokens and their contracts via JSONRPC.

The following endpoints are supplied by this blueprint:

    * [GET] `/tokens`
        List details of all known token contracts.

    * [POST, GET]`/tokens/<token_address>`
        List the details of the contract matching the given address.
        When using POST, the contract will be created instead. The
        required parameters for this must be submitted as form data.

    * [POST] `/tokens/<token_address>/mint`
        Mint a number of tokens for a given address. `token_address` determines
        what token contract is used to do this.aa
"""

import structlog
from eth_utils.address import to_canonical_address, to_checksum_address
from flask import Blueprint, Response, jsonify, request
from raiden_contracts.constants import CONTRACT_CUSTOM_TOKEN, CONTRACT_USER_DEPOSIT
from raiden_contracts.contract_manager import (
    ContractManager,
    contracts_precompiled_path,
    gas_measurements,
)

from raiden.network.rpc.client import JSONRPCClient, SmartContractCall, TransactionEstimated
from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.rpc.schemas.tokens import ContractTransactSchema, TokenCreateSchema

tokens_blueprint = Blueprint("tokens_blueprint", __name__)

CONTRACT_MANAGER = ContractManager(contracts_precompiled_path())
GAS_PRICES = gas_measurements()


token_create_schema = TokenCreateSchema()
token_transact_schema = ContractTransactSchema()

#: Valid actions to pass when calling `POST /rpc/contract/<action>`.
TRANSACT_ACTIONS = {
    "allowance": ("approve", CONTRACT_CUSTOM_TOKEN, GAS_PRICES["CustomToken.approve"]),
    "mint": ("mintFor", CONTRACT_CUSTOM_TOKEN, GAS_PRICES["CustomToken.mint"]),
    "deposit": ("deposit", CONTRACT_USER_DEPOSIT, GAS_PRICES["UserDeposit.deposit"]),
}

log = structlog.getLogger(__name__)


@tokens_blueprint.route("/rpc/contract", methods=["POST"])
def deploy_token():
    """Deploy a new token contract.

    ---
    parameters:
      - name: client_id
        in: query
        required: true
        schema:
          type: string

    post:
      description": "Deploy a new token contract."
      parameters:
        - name: constructor_args
          in: query
          required: true
          schema:
            type: object
            properties:
              decimals:
                type: integer
                format: int32
              name:
                type: string
              symbol:
                type: string

        - name: token_name
          in: query
          required: false
          schema:
            type: string

      responses:
        200:
          description: "Address and deployment block of the deployed contract."
          content:
            application/json:
              schema: {$ref: '#/components/schemas/TokenCreateSchema'}

    """
    with REDMetricsTracker():
        log.info("Processing Token Contract Deployment Request", request=request)
        data = token_create_schema.validate_and_deserialize(request.get_json())
        rpc_client = data["client"]
        token_name = data.get("token_name") or data["constructor_args"][1]

        contract_manager = ContractManager(contracts_precompiled_path())

        constructor_args = data["constructor_args"]

        decimals, name, symbol = (
            constructor_args["decimals"],
            constructor_args["name"],
            constructor_args["symbol"],
        )

        log.info(
            "deploying contract",
            constructor_parameters=(1, decimals, name, symbol),
            client_id=rpc_client.client_id,
        )

        token_contract, receipt = rpc_client.deploy_single_contract(
            "CustomToken",
            contract_manager.get_contract("CustomToken"),
            constructor_parameters=(1, decimals, name, symbol),
        )

        contract_address = to_checksum_address(token_contract.address)
        log.debug(
            "Received deployment receipt", receipt=receipt, contract_address=contract_address
        )

        deployment_block = receipt["blockNumber"]
        dumped = token_create_schema.dump(
            {
                "contract": {"address": contract_address, "name": token_name},
                "deployment_block": deployment_block,
            }
        )
        log.info("Token Contract deployed", receipt=dumped)
        return jsonify(dumped)


@tokens_blueprint.route("/rpc/contract/<action>", methods=["POST"])
def call_contract(action):
    """Execute an action for the given token contract and the given target address.

    `action` may be one of :var:`.TRANSACT_ACTIONS` keys.
    ---
    parameters:
      - name: client_id
        in: query
        required: true
        schema:
          type: string

    post:
      description": >
        Execute an action for a contract at `contract_address` for the given `target_address`
      parameters:
        - name: contract_address
          in: query
          required: true
          schema:
            type: string

        - name: target_address
          in: query
          required: true
          schema:
            type: string

        - name: gas_limit
          in: query
          required: true
          schema:
            type: number
            format: int

        - name: amount
          in: query
          required: true
          schema:
            type: number
            format: int

      responses:
        200:
          description: "Transaction hash of the contract transact request."
          content:
            application/json:
              schema: {$ref: '#/components/schemas/ContractTransactSchema'}
    """

    with REDMetricsTracker():
        if action not in TRANSACT_ACTIONS:
            return Response(
                status=400, response=f"'action' must be one of {TRANSACT_ACTIONS.keys()}"
            )
        data = token_transact_schema.validate_and_deserialize(request.get_json())

        tx_hash = transact_call(action, data)

        dumped = token_transact_schema.dump({"tx_hash": tx_hash})
        return jsonify(dumped)


def transact_call(key, data):
    rpc_client: JSONRPCClient = data["client"]

    action, contract, gas_price = TRANSACT_ACTIONS[key]

    log.debug("Fetching ABI..", contract=contract)
    contract_abi = CONTRACT_MANAGER.get_contract_abi(contract)

    log.debug(
        "Fetching contract proxy",
        contract=contract,
        abi=contract_abi,
        contract_address=data["contract_address"],
    )
    contract = rpc_client.new_contract_proxy(
        abi=contract_abi, contract_address=to_canonical_address(data["contract_address"])
    )

    log.debug("Preparing transaction...", action=action, **data)
    args = data["amount"], data["target_address"]
    if action != "mintFor":
        # The deposit function expects the address first, amount second.
        args = (data["target_address"], data["amount"])

    # By default the RPCClient API requires a gas estimation before being able to transact
    # This leads to problems here, where multiple dependent transaction (e.g. `approve`
    # and `deposit`) are sent.
    # This is circumvented by creating a `TransactionEstimated` object by hand, as we know the
    # transactions will be valid.
    block = rpc_client.web3.eth.getBlock("latest")
    transaction = TransactionEstimated(
        from_address=rpc_client.address,
        data=SmartContractCall(contract=contract, function=action, args=args, kwargs={}, value=0),
        eth_node=rpc_client.eth_node,
        extra_log_details={},
        estimated_gas=int(gas_price * 2),
        gas_price=int(rpc_client.web3.eth.gasPrice * 1.5),
        approximate_block=(block["hash"], block["number"]),
    )
    log.debug("Sending transaction...", transaction=transaction)
    transaction_hash = rpc_client.transact(transaction)

    return transaction_hash
