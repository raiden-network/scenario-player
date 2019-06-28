import pluggy

from scenario_player.constants import HOST_NAMESPACE


HOOK_IMPL = pluggy.hooks.HookimplMarker(HOST_NAMESPACE)
