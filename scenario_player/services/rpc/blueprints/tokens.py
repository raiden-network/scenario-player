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
from eth_utils.address import to_checksum_address
from flask import Blueprint, jsonify, request
from raiden_contracts.constants import CONTRACT_CUSTOM_TOKEN
from raiden_contracts.contract_manager import ContractManager, contracts_precompiled_path

from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.rpc.schemas.tokens import TokenCreateSchema, TokenMintSchema

tokens_blueprint = Blueprint("tokens_blueprint", __name__)


token_create_schema = TokenCreateSchema()
token_mint_schema = TokenMintSchema()


@tokens_blueprint.route("/rpc/token", methods=["POST"])
def deploy_token():
    """Deploy a new token contract.

    Example::

        POST /rpc/token

            {
                "client_id": <str>,
                "constructor_args": {
                    "decimals": <int>,
                    "name": <str>,
                    "symbol: <str>,
                }
                "token_name": <str (optional)>,
            }

        200 OK

            {
                "address": <str>,
                "deployment_block": <int>,
            }

    If `token_name` is not given, we'll use constructor_args["name"] instead.

    """
    with REDMetricsTracker():

        data = token_create_schema.validate_and_deserialize(request.get_json())
        rpc_client = data["client"]
        # token_name = data.get("token_name") or data["constructor_args"][1]

        contract_manager = ContractManager(contracts_precompiled_path())

        constructor_args = data["constructor_args"]

        decimals, name, symbol = (
            constructor_args["decimals"],
            constructor_args["name"],
            constructor_args["symbol"],
        )

        token_contract, receipt = rpc_client.deploy_single_contract(
            "CustomToken",
            contract_manager.get_contract("CustomToken"),
            constructor_parameters=(1, decimals, name, symbol),
        )
        contract_address = to_checksum_address(token_contract.contract_address)
        deployment_block = receipt["blockNum"]
        dumped = token_create_schema.dump(
            {"address": contract_address, "deployment_block": deployment_block}
        )
        return jsonify(dumped)


@tokens_blueprint.route("/rpc/token/mint", methods=["POST"])
def mint_token():
    """Mint new tokens at the given token contract for the given target address.

    Example::

        POST /rpc/token/mint

            {
                "client_id": <str>,
                "contract_address": <str>,
                "target_address": <str>,
                "gas_limit": <float>,
                "amount": <float>,
            }

        200 OK

            {
                "tx_hash": <str>,
            }
    """
    with REDMetricsTracker():
        data = token_mint_schema.validate_and_deserialize(request.get_json())
        rpc_client = data["client"]

        contract_manager = ContractManager(contracts_precompiled_path())

        token_specs = contract_manager.get_contract(CONTRACT_CUSTOM_TOKEN)
        token_proxy = rpc_client.new_contract_proxy(token_specs["abi"], data["contract_address"])
        tx_hash = token_proxy.transact(
            "mintFor", data["gas_limit"], data["amount"], data["target_address"]
        )
        dumped = token_mint_schema.dump({"tx_hash": tx_hash})
        return jsonify(dumped)
