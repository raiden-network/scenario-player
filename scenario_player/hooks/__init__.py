import logging

import pluggy

from scenario_player.constants import HOST_NAMESPACE
from scenario_player.hooks import specs
from scenario_player.hooks import impl

log = logging.getLogger(__name__)


def get_plugin_manager(namespace):
    """Fetch pluggy's plugin manager for our library."""
    pm = pluggy.PluginManager(namespace)
    log.info("Loading Hook Specifications..")
    pm.add_hookspecs(specs)

    log.info("Loading Hook Implemenations from entry points..")
    pm.load_setuptools_entrypoints(namespace)

    log.info("Registering Hook Implementations in scenario_player..")
    pm.register(impl)
    return pm


SP_PM = get_plugin_manager(HOST_NAMESPACE)
