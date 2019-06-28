import sys
from typing import List, Union

import flask
import pluggy

#: The namespace plugins should use as a prefix when creating a :class:`pluggy.HookimplMarker`.
HOST_NAMESPACE = "scenario_player"

#: Hook Specification Object for specifying new hooks.
HOOK_SPEC = pluggy.hooks.HookspecMarker(HOST_NAMESPACE)

#: Hook Implementer object for implementing available hooks.
HOOK_IMPL = pluggy.hooks.HookimplMarker(HOST_NAMESPACE)


def get_plugin_manager(namespace):
    """Fetch pluggy's plugin manager for our library."""
    pm = pluggy.PluginManager(namespace)
    pm.add_hookspecs(HOOK_SPEC)
    pm.load_setuptools_entrypoints(namespace)
    pm.register(namespace)
    return pm


def register_hook_specifications(library):
    pm = get_plugin_manager(library)
    # load all hookimpls from the local module's namespace
    pm.add_hookspecs(sys.modules[library])


register_hook_specifications(HOST_NAMESPACE)
#: A list of all blueprints currently registered with the library.
PLUGIN_BLUEPRINTS = [
    blueprints
    for blueprints in get_plugin_manager(HOST_NAMESPACE).hook.register_blueprints()
    if blueprints
]


def register_hook_implementations(library):
    pm = get_plugin_manager(library)
    # load all hookimpls from the local module's namespace
    pm.register(sys.modules[library])


@HOOK_SPEC
def register_blueprints() -> Union[None, List[flask.Blueprint]]:
    """Register a list of blueprints with :mode:`raiden-scenario-player`."""
