from typing import List, Union

import flask
import pluggy


HOOK_SPEC = pluggy.hooks.HookspecMarker("scenario_player")


@HOOK_SPEC
def register_blueprints() -> Union[None, List[flask.Blueprint]]:
    """Register a list of blueprints with :mode:`raiden-scenario-player`."""
