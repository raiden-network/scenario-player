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
import json

import structlog
from eth_utils.address import to_checksum_address
from flask import Blueprint, abort, jsonify, request
from raiden_contracts.constants import CONTRACT_CUSTOM_TOKEN, CONTRACT_USER_DEPOSIT
from raiden_contracts.contract_manager import ContractManager, contracts_precompiled_path

from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.rpc.schemas.tokens import TokenCreateSchema, TokenMintSchema

tokens_blueprint = Blueprint("tokens_blueprint", __name__)


token_create_schema = TokenCreateSchema()
token_mint_schema = TokenMintSchema()


log = structlog.getLogger(__name__)


@tokens_blueprint.route("/rpc/token", methods=["POST"])
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
        try:
            token_contract, receipt = rpc_client.deploy_single_contract(
                "CustomToken",
                contract_manager.get_contract("CustomToken"),
                constructor_parameters=(1, decimals, name, symbol),
            )
        except ValueError as e:
            try:
                json.loads(str(e))
            except json.JSONDecodeError:
                raise e

            abort(status=400, response=str(e))
        contract_address = to_checksum_address(token_contract.contract_address)
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


@tokens_blueprint.route("/rpc/token/mint", methods=["POST"])
def mint_contract():
    """Mint new tokens at the given token contract for the given target address.

    ---
    parameters:
      - name: client_id
        in: query
        required: true
        schema:
          type: string

    post:
      description": "Mint a token at `contract_address` for the given `target_address`",
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
            format: float

        - name: amount
          in: query
          required: true
          schema:
            type: number
            format: float

      responses:
        200:
          description: "Transaction hash of the mint request."
          content:
            application/json:
              schema: {$ref: '#/components/schemas/TokenMintSchema'}
    """

    with REDMetricsTracker():
        data = token_mint_schema.validate_and_deserialize(request.get_json())

        tx_hash = transact_call(data, CONTRACT_CUSTOM_TOKEN)

        dumped = token_mint_schema.dump({"tx_hash": tx_hash})
        return jsonify(dumped)


@tokens_blueprint.route("/rpc/token/allowance", methods=["PUT"])
def contract_allowance():
    """Update the allowance for a User Deposit Contract.

    ---
    parameters:
      - name: client_id
        in: query
        required: true
        schema:
          type: string

    post:
      description": >
        Set the allowance of a UserDeposit Contract at `contract_address`
        for the given `target_address`
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
            format: float

        - name: amount
          in: query
          required: true
          schema:
            type: number
            format: float

      responses:
        200:
          description: "Transaction hash of the mint request."
          content:
            application/json:
              schema: {$ref: '#/components/schemas/TokenMintSchema'}
    """
    with REDMetricsTracker():
        data = token_mint_schema.validate_and_deserialize(request.get_json())

        tx_hash = transact_call(data, CONTRACT_USER_DEPOSIT)

        dumped = token_mint_schema.dump({"tx_hash": tx_hash})
        return jsonify(dumped)


def transact_call(data, contract):
    transact_actions = {CONTRACT_USER_DEPOSIT: "approve", CONTRACT_CUSTOM_TOKEN: "mintFor"}

    rpc_client = data["client"]
    contract_manager = ContractManager(contracts_precompiled_path())

    log.info("Minting tokens", contract=contract)
    token_abi = contract_manager.get_contract_abi(contract)
    token_proxy = rpc_client.new_contract_proxy(token_abi, data["contract_address"])
    log.debug("Transacting..", **data)
    return token_proxy.transact(
        transact_actions[contract], data["gas_limit"], data["amount"], data["target_address"]
    )
