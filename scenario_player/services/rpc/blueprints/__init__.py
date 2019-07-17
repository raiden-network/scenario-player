import pluggy

from scenario_player.constants import HOST_NAMESPACE
from scenario_player.services.rpc.blueprints.transactions import transactions_blueprint
from scenario_player.services.rpc.blueprints.instances import instances_blueprint

__all__ = ["transactions_blueprint", "instances_blueprint"]


HOOK_IMPL = pluggy.HookimplMarker(HOST_NAMESPACE)


@HOOK_IMPL
def register_blueprints(app):
    for bp in (transactions_blueprint, instances_blueprint):
        app.register_blueprint(bp)
