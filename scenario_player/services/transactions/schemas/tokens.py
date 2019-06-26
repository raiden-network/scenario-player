from marshmallow.fields import Number, String, List
from scenario_player.services.common.schemas import ValidatorSchema


class TokenListSchema(ValidatorSchema):
    """Validator for GET /tokens requests."""
    tx_hashes = List(String(), required=True, load_only=True)


class TokenMintSchema(ValidatorSchema):
    """Validator for POST /token/<token_address>/mint requests."""
    token_address = String(load_only=True)
    mint_target = String(load_only=True)
    amount = Number(load_only=True)


class TokenCreateSchema(ValidatorSchema):
    """Validator for POST /token/<token_address> requests."""


class TokenDetailsSchema(ValidatorSchema):
    """Validator for GET /tokens/<token_address> requests."""
