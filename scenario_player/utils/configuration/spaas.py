import structlog
from eth_utils import encode_hex

from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class SPaaSServiceConfig(ConfigMapping):
    """SPaaS Configuration for a single micro service.

    Provides the host, port, netloc and scheme from the
    scenario definition, if specified; if not specified, provides
    defaults for these values.

    `netloc` is auto-generated from `port` and `host`, and must
    not be specified in the definition file.

    Example scenario definition section::

        >my_scenario.yaml
        version: 2
        ...
        spaas:
          my_service:
            scheme: http
            port: 80
            host: myhost.com
        ...

    """

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.dict!r})"

    @property
    def scheme(self):
        return self.get("scheme", "http")

    @property
    def host(self):
        return self.get("host", "127.0.0.1")

    @property
    def port(self):
        return self.get("port", "5000")

    @property
    def netloc(self):
        return f"{self.host}:{self.port}"


class SPaaSConfig(ConfigMapping):
    def __init__(self, loaded_definition: dict):
        super(SPaaSConfig, self).__init__(loaded_definition.get("spaas") or {})
        self.rpc = RPCServiceConfig(self.dict)


class RPCServiceConfig(SPaaSServiceConfig):
    def __init__(self, spaas_config: dict):
        super(RPCServiceConfig, self).__init__(spaas_config.get("rpc") or {})
        self.client_id = None

    def assign_rpc_instance(self, runner, privkey, gas_price):
        """Assign this SP instance an RPC Client to use when making write-requests."""
        params = {
            "chain_url": runner.definition.settings.eth_client_rpc_address,
            "privkey": encode_hex(privkey),
            "gas_price": gas_price,
        }
        resp = runner.service_session.post("spaas://rpc/client", json=params)
        client_id = resp.json()["client_id"]
        self.client_id = client_id
