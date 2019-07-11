from typing import List, Union

import flask
import pluggy

from scenario_player.constants import HOST_NAMESPACE

HOOK_SPEC = pluggy.hooks.HookspecMarker(HOST_NAMESPACE)


@HOOK_SPEC
def register_blueprints() -> Union[None, List[flask.Blueprint]]:
    """Register a list of blueprints with :mode:`raiden-scenario-player`."""
