from marshmallow.fields import Float, List, String

from scenario_player.services.common.schemas import BytesField, ValidatorSchema


class TransactionSendSchema(ValidatorSchema):
    """Validator for POST /transaction requests"""

    # Serialization fields.
    to = String(required=True, load_only=True)
    start_gas = Float(required=True, load_only=True)
    value = Float(required=True, load_only=True)

    # Deserialization fields.
    tx_hash = BytesField(required=True, dump_only=True)


class TransactionTrackRequest(ValidatorSchema):
    """Validator for GET /transaction requests"""

    # Serialization fields.
    hashes = List(BytesField(), required=True, load_only=True)

    # Deserialization fields.
    missing = List(BytesField(), missing=[], dump_only=True)
    found = List(BytesField(), missing=[], dump_only=True)
