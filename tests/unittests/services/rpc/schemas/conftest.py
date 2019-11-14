import flask
import pytest

from scenario_player.services.rpc.schemas.tokens import TokenCreateSchema, ContractTransactSchema
from scenario_player.services.rpc.utils import RPCRegistry, RPCClient


@pytest.fixture
def hexed_client_id():
    return str(b"test-client-id".hex())


@pytest.fixture
def base_request_params(hexed_client_id):
    """Parameters required by the Schemas under testing in this module, but not under testing themselves.

    i.e. they're already tested somewhere else.
    """
    return {"client_id": hexed_client_id}


@pytest.fixture
def deserialized_base_params(app, base_request_params):
    deserialized = dict(base_request_params)
    deserialized["client"] = app.config["rpc-client"][base_request_params["client_id"]]
    return deserialized


@pytest.fixture
def app(hexed_client_id):

    bp = flask.Blueprint("test_views", __name__)

    @bp.route("/test-create", methods=["POST"])
    def create_token():
        TokenCreateSchema().validate_and_deserialize(flask.request.form)
        return "ok"

    @bp.route("/test-mint", methods=["POST"])
    def mint_token():
        ContractTransactSchema().validate_and_deserialize(flask.request.form)
        return "ok"

    registry = RPCRegistry()
    registry.dict[hexed_client_id] = mock.MagicMock(spec=RPCClient, client_id=hexed_client_id)

    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.config["rpc-client"] = registry

    app.register_blueprint(bp)

    return app
