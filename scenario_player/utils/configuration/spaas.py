import structlog

from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class SPaaSServiceConfig(ConfigMapping):
    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.dict!r})"

    @property
    def scheme(self):
        return self.get("scheme", "https")

    @property
    def host(self):
        return self.get("host", "localhost")

    @property
    def port(self):
        return self.get("port", "5000")

    @property
    def netloc(self):
        return f"{self.host}:{self.port}"


class SPaaSConfig(ConfigMapping):
    def __init__(self, loaded_yaml: dict):
        super(SPaaSConfig, self).__init__(loaded_yaml.get("spaas", {}))

    @property
    def rpc(self) -> SPaaSServiceConfig:
        return SPaaSServiceConfig(self.get("rpc", {}))
