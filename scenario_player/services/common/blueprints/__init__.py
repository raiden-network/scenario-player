import pluggy

from scenario_player.constants import HOST_NAMESPACE
from scenario_player.services.common.blueprints.admin import admin_blueprint
from scenario_player.services.common.blueprints.metrics import metrics_blueprint

__all__ = ["admin_blueprint", "metrics_blueprint"]


HOOK_IMPL = pluggy.HookimplMarker(HOST_NAMESPACE)


@HOOK_IMPL
def register_blueprints(app):
    for bp in (admin_blueprint, metrics_blueprint):
        app.register_blueprint(bp)
