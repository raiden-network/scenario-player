import flask
import pluggy

from scenario_player.constants import HOST_NAMESPACE

HOOK_SPEC = pluggy.hooks.HookspecMarker(HOST_NAMESPACE)


@HOOK_SPEC
def register_blueprints(app: flask.Flask) -> None:
    """Register a list of blueprints with the :mod:`raiden-scenario-player` applcation."""
