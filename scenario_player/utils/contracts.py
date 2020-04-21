from typing import Tuple

from eth_typing import ChecksumAddress
from eth_utils import to_canonical_address
from raiden_contracts.constants import CONTRACT_TOKEN_NETWORK_REGISTRY, CONTRACT_USER_DEPOSIT
from raiden_contracts.contract_manager import (
    ContractManager,
    DeployedContracts,
    contracts_precompiled_path,
    get_contracts_deployment_info,
)

from raiden.network.proxies.custom_token import CustomToken
from raiden.network.proxies.proxy_manager import ProxyManager, ProxyManagerMetadata
from raiden.network.proxies.user_deposit import UserDeposit
from raiden.network.rpc.client import JSONRPCClient
from raiden.settings import RAIDEN_CONTRACT_VERSION
from raiden.utils.typing import BlockNumber, ChainID, UserDepositAddress


def get_proxy_manager(client: JSONRPCClient, deploy: DeployedContracts) -> ProxyManager:
    contract_manager = ContractManager(contracts_precompiled_path(RAIDEN_CONTRACT_VERSION))

    assert "contracts" in deploy, deploy
    token_network_deployment_details = deploy["contracts"][CONTRACT_TOKEN_NETWORK_REGISTRY]
    deployed_at = token_network_deployment_details["block_number"]
    token_network_registry_deployed_at = BlockNumber(deployed_at)

    return ProxyManager(
        client,
        contract_manager,
        ProxyManagerMetadata(
            token_network_registry_deployed_at=token_network_registry_deployed_at,
            filters_start_at=token_network_registry_deployed_at,
        ),
    )


def get_udc_and_corresponding_token_from_dependencies(
    chain_id: ChainID, proxy_manager: ProxyManager, udc_address: ChecksumAddress = None
) -> Tuple[UserDeposit, CustomToken]:
    """ Return contract proxies for the UserDepositContract and associated token.

    This will return a proxy to the `UserDeposit` contract as determined by the
    **local** Raiden depedency.
    """
    if udc_address is None:

        contracts = get_contracts_deployment_info(chain_id, version=RAIDEN_CONTRACT_VERSION)

        msg = (
            f"invalid chain_id, {chain_id} is not available for version {RAIDEN_CONTRACT_VERSION}"
        )
        assert contracts, msg

        udc_address = contracts["contracts"][CONTRACT_USER_DEPOSIT]["address"]

    userdeposit_proxy = proxy_manager.user_deposit(
        UserDepositAddress(to_canonical_address(udc_address)), "latest"
    )

    token_address = userdeposit_proxy.token_address("latest")
    user_token_proxy = proxy_manager.custom_token(token_address, "latest")

    return userdeposit_proxy, user_token_proxy
