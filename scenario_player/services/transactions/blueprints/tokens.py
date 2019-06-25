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
from flask import Blueprint, abort

from scenario_player.services.common.metrics import REDMetricsTracker
from scenario_player.services.transactions.schemas.tokens import (
    TokenCreateRequest,
    TokenCreateResponse,
    TokenListRequest,
    TokenListResponse,
    TokenMintRequest,
    TokenMintResponse,
)

tokens_view = Blueprint("tokens_view", __name__)


@tokens_view.add_route('/tokens', methods=["GET"])
def tokens_view():
    handlers = {
        "GET": list_tokens,
    }
    with REDMetricsTracker(request.method, '/tokens'):
        return handlers[request.method]()


def list_tokens():
    """Return a list of all available token contracts and their data.

    Example::

        GET /tokens

        200 OK

            {
                "tokens": [
                    TODO: Determine what this is going to look like.
                ]
            }
    """
    data = TokenListRequest().validate_and_serialize(request.args)
    abort(501)
    return TokenListResponse().dump(data)


@tokens_view.add_route('/tokens/<token_address>', methods=["POST", "GET"])
def token_details_view(token_address):
    handlers = {
        "POST": create_token,
        "GET": get_token,
    }
    with REDMetricsTracker(request.method, '/tokens/<token_address>'):
        return handlers[request.method]()


def create_token():
    """Deploy a given token contract.

    If the contract already exists, we return its data instead; otherwise,
    we create the contract via JSONRPC.

    Example::

        POST /tokens/<token_address>

            {
                TODO: Determine what this is going to look like.
            }

        200 OK
    """
    data = TokenCreateRequest().validate_and_serialize(request.form)
    abort(501)
    return TokenCreateResponse().dump(data)


def get_token(token_address):
    """Fetch details about a token by the given `token_address`.

    Example::

        GET /tokens/<token_address>

        200 OK

            {
                TODO: Determine what this is going to look like.
            }
    """
    data = TokenDetailsRequest().validate_and_serialize(request.args)
    abort(501)
    return TokenDetailsResponse().dump(data)


@token_contracts_view.add_route('/tokens/<token_address>/mint', methods=["POST"])
def mint_token_view(token_address):
    """Mint tokens for the given token address.."""
    handlers = {
        "POST": mint_token,
    }
    with REDMetricsTracker(request.method, '/tokens/<token_address>'):
        return handlers[request.method](token_address)


def mint_token(token_address):
    """Mint a number of tokens of the token at given `token_address`.

    Example::

        POST /tokens/<token_address>/mint

            {
                "mint_target": <wallet_address>,
                "amount", <float>,
            }

        200 OK

            {
                TODO: Determine what this is going to look like.
            }
    """
    data = TokenMintRequest().validate_and_serialize(request.form)
    abort(501)
    return TokenMintResponse().dump(data)
