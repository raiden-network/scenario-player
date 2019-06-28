import pluggy

from scenario_player.constants import HOST_NAMESPACE
from scenario_player.hooks import impl, specs


def get_plugin_manager(namespace):
    """Fetch pluggy's plugin manager for our library."""
    pm = pluggy.PluginManager(namespace)
    print(pm.__dict__)
    pm.add_hookspecs(specs)
    pm.load_setuptools_entrypoints(namespace)
    pm.register(impl)
    return pm


SP_PM = get_plugin_manager(HOST_NAMESPACE)

#: A list of all blueprints currently registered with the library.
PLUGIN_BLUEPRINTS = [blueprints for blueprints in SP_PM.hook.register_blueprints() if blueprints]
