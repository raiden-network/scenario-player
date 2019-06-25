from marshmallow.fields import Float, List, String

from scenario_player.services.common.schemas import BytesField, ValidatorSchema, SerializerSchema


class TransactionSendRequest(ValidatorSchema):
    """Validator for POST /transaction requests"""
    to = String(required=True)
    start_gas = Float(required=True)
    value = Float(required=True)


class TransactionSendResponse(SerializerSchema):
    """Serializer for POST /transaction responses"""
    tx_hash = BytesField(required=True)


class TransactionTrackRequest(ValidatorSchema):
    """Validator for GET /transaction requests"""

    hashes = List(BytesField(), required=True)


class TransactionTrackResponse(SerializerSchema):
    """Serializer for GET /transaction responses"""
    missing = List(BytesField(), missing=[])
    found = List(BytesField(), missing=[])
