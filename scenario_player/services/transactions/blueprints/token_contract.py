from flask import Blueprint, abort

from scenario_player.services.common.metrics import REDMetricsTracker

token_contracts_view = Blueprint("transactions_view", __name__)


@token_contracts_view.add_route('/token_contracts', methods=["POST", "GET"])
def token_contracts_view():
    handlers = {
        "GET": get_contract_data,
        "POST": deploy_contract,
    }
    with REDMetricsTracker(request.method, '/token_contracts'):
        handlers[request.method]()


def get_contract_data():
    abort(501)


def deploy_contract():
    abort(501)

