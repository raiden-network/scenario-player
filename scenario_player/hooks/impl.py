"""Hook Implementations collected from the :mod:`scenario_player.services`  sub-package.

Dynamically loads any modules containing functions or methods decorated with
:class:`HookImplMarker("scenario_player")` from the :mod:`scenario_player.services`
package.

It's the service author's responsibility to list the modules with hook implementations
in the services __init__.py file, in a variable called :var:`__hooks__`. Otherwise
the hook implementations will not be detected.
"""
import logging
import importlib
import pkgutil

from scenario_player import services as services_subpackage


def load_hook_modules_to_namespace():
    for sub_module in pkgutil.iter_modules(path=services_subpackage.__path__):
        _, sub_module_name, _ = sub_module

        if sub_module_name.startswith(("_", "utils")):
            continue

        possible_blueprints_module_path = f"{services_subpackage.__name__}.{sub_module_name}.blueprints"
        service_pkg_path = services_subpackage.__name__ + "." + sub_module_name

        try:
            importlib.import_module(possible_blueprints_module_path)
        except ImportError:
            logging.error(f"skipped {sub_module_name} service - no blueprints module found!")
            continue
        else:
            logging.info(f"Loaded blueprints for {service_pkg_path} service..")


load_hook_modules_to_namespace()
