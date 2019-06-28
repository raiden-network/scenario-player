from typing import List, Union

import flask
import pluggy


def get_plugin_manager():
    """Fetch pluggy's plugin manager for our library."""
    pm = pluggy.PluginManager("bitex")
    pm.add_hookspecs(specs)
    pm.load_setuptools_entrypoints("bitex")
    pm.register(base)
    return pm


pm = get_plugin_manager()


PLUGIN_BLUEPRINTS = [blueprints for blueprints in pm.hook.register_blueprints() if blueprints]
PLUGIN_NAMESPACE = "raiden-scenario-player"
hook_spec = pluggy.hooks.HookspecMarker(PLUGIN_NAMESPACE)


@hook_spec
def register_blueprints() -> Union[None, List[flask.Blueprint]]:
    """Register a list of blueprints with :mode:`raiden-scenario-player`."""
