import pluggy

from scenario_player.hooks import impl, specs

#: The namespace plugins should use as a prefix when creating a :class:`pluggy.HookimplMarker`.
HOST_NAMESPACE = "scenario_player"


def get_plugin_manager(namespace):
    """Fetch pluggy's plugin manager for our library."""
    pm = pluggy.PluginManager(namespace)
    print(pm.__dict__)
    pm.add_hookspecs(specs)
    pm.load_setuptools_entrypoints(namespace)
    pm.register(impl)
    return pm


SP_PM = get_plugin_manager("scenario_player")

#: A list of all blueprints currently registered with the library.
PLUGIN_BLUEPRINTS = [
    blueprints
    for blueprints in SP_PM.hook.register_blueprints()
    if blueprints
]
