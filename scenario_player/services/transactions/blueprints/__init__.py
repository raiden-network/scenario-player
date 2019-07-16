import pluggy

from scenario_player.constants import HOST_NAMESPACE
from scenario_player.services.transactions.blueprints.transactions import transactions_blueprint

__all__ = ["transactions_blueprint"]


HOOK_IMPL = pluggy.HookimplMarker(HOST_NAMESPACE)


@HOOK_IMPL
def register_blueprints(app):
    for bp in (transactions_blueprint,):
        app.register_blueprint(bp)
