from typing import Callable, Dict

from web3.gas_strategies.time_based import fast_gas_price_strategy, medium_gas_price_strategy

DEFAULT_TOKEN_BALANCE_MIN = 5_000
DEFAULT_TOKEN_BALANCE_FUND = 50_000
OWN_ACCOUNT_BALANCE_MIN = 30 * 10 ** 18  # := 30.0 ETH
NODE_ACCOUNT_BALANCE_MIN = 15 * 10 ** 16  # := 0.15 ETH
NODE_ACCOUNT_BALANCE_FUND = 3 * 10 ** 18  # := 3.0 ETH
TIMEOUT = 200
API_URL_TOKEN_NETWORK_ADDRESS = "{protocol}://{target_host}/api/v1/tokens/{token_address}"
MAX_RAIDEN_STARTUP_TIME = 2000  # seconds
MAX_API_TASK_TIMEOUT = 30 * 60  # seconds

#: Available gas price strategies selectable by passing their key to the
#: settings.gas_price config option in the scenario definition.
GAS_STRATEGIES: Dict[str, Callable] = {
    "FAST": fast_gas_price_strategy,
    "MEDIUM": medium_gas_price_strategy,
}

# DO NOT CHANGE THIS! It would break backwards compatibility, since i.e. wallet generation
# depends on it!!!
RUN_NUMBER_FILENAME = "run_number.txt"
