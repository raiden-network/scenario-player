from marshmallow.fields import Number, String, List
from scenario_player.services.common.schemas import ValidatorSchema


class TokenListRequest(ValidatorSchema):
    """Validator for GET /tokens requests."""
    tx_hashes = List(String(), required=True, load_only=True)


class TokenMintRequest(ValidatorSchema):
    """Validator for POST /token/<token_address>/mint requests."""
    token_address = String(load_only=True)
    mint_target = String(load_only=True)
    amount = Number(load_only=True)


class TokenCreateRequest(ValidatorSchema):
    """Validator for POST /token/<token_address> requests."""


class TokenDetailsRequest(ValidatorSchema):
    """Validator for GET /tokens/<token_address> requests."""
