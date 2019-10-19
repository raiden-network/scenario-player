import enum

from web3.gas_strategies.time_based import fast_gas_price_strategy, medium_gas_price_strategy

#: The namespace plugins should use as a prefix when creating a :class:`pluggy.HookimplMarker`.
HOST_NAMESPACE = "scenario_player"

DEFAULT_TOKEN_BALANCE_MIN = 5_000
DEFAULT_TOKEN_BALANCE_FUND = 50_000
OWN_ACCOUNT_BALANCE_MIN = 5 * 10 ** 17  # := 0.5 Eth
NODE_ACCOUNT_BALANCE_MIN = 15 * 10 ** 16  # := 0.15 Eth
NODE_ACCOUNT_BALANCE_FUND = 3 * 10 ** 17  # := 0.3 Eth
TIMEOUT = 200
API_URL_ADDRESS = "{protocol}://{target_host}/api/v1/address"
API_URL_TOKENS = "{protocol}://{target_host}/api/v1/tokens"
API_URL_TOKEN_NETWORK_ADDRESS = "{protocol}://{target_host}/api/v1/tokens/{token_address}"
SUPPORTED_SCENARIO_VERSIONS = {2}

#: Available gas price strategies selectable by passing their key to the
#: settings.gas_price config option in the scenario yaml.
GAS_STRATEGIES = {"FAST": fast_gas_price_strategy, "MEDIUM": medium_gas_price_strategy}

GAS_LIMIT_FOR_TOKEN_CONTRACT_CALL = 100_000

RUN_NUMBER_FILENAME = "run_number.txt"


class NodeMode(enum.Enum):
    EXTERNAL = 1
    MANAGED = 2
