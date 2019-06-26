from marshmallow.fields import Number, String
from scenario_player.services.common.schemas import ValidatorSchema, SerializerSchema


class TokenListRequest(ValidatorSchema):
    """Validator for GET /tokens requests."""


class TokenListResponse(SerializerSchema):
    """Serializer for GET /tokens responses."""


class TokenMintRequest(ValidatorSchema):
    """Validator for POST /token/<token_address>/mint requests."""
    token_address = String()
    mint_target = String()
    amount = Number()


class TokenMintResponse(SerializerSchema):
    """Serializer for POST /token/<token_address>/mint responses."""


class TokenCreateRequest(ValidatorSchema):
    """Validator for POST /token/<token_address> requests."""


class TokenCreateResponse(SerializerSchema):
    """Serializer for POST /token/<token_address> responses."""
    pass


class TokenDetailsRequest(ValidatorSchema):
    """Validator for GET /tokens/<token_address> requests."""


class TokenDetailsResponse(SerializerSchema):
    """Serializer for GET /tokens/<token_address> responses."""
