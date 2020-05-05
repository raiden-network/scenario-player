import json
from typing import cast

import gevent
import structlog
from eth_utils import to_hex
from eth_utils.typing import ChecksumAddress
from gevent import Greenlet
from typing_extensions import TypedDict

from raiden.network.proxies.custom_token import CustomToken
from raiden.network.proxies.user_deposit import UserDeposit
from raiden.network.rpc.client import EthTransfer, JSONRPCClient
from raiden.utils.typing import Address, Set, TokenAmount
from scenario_player.exceptions.config import TokenFileError, TokenFileMissing

CUSTOM_TOKEN_NAME = "CustomToken"

log = structlog.get_logger(__name__)


TokenDetails = TypedDict("TokenDetails", {"name": str, "address": ChecksumAddress, "block": int})


def token_maybe_mint(
    token_proxy: CustomToken, target_address: Address, minimum_balance: int, maximum_balance: int
) -> None:
    current_balance = token_proxy.balance_of(target_address)

    if minimum_balance > current_balance:
        mint_amount = TokenAmount(maximum_balance - current_balance)
        token_proxy.mint_for(amount=mint_amount, address=target_address)


def eth_maybe_transfer(
    orchestration_client: JSONRPCClient,
    target: Address,
    minimum_balance: int,
    maximum_balance: int,
) -> None:
    balance = orchestration_client.balance(target)

    if balance < minimum_balance:
        eth_transfer = EthTransfer(
            to_address=target,
            value=maximum_balance - balance,
            gas_price=orchestration_client.web3.eth.gasPrice,
        )
        tx_hash = orchestration_client.transact(eth_transfer)
        orchestration_client.poll_transaction(tx_hash)


def userdeposit_maybe_increase_allowance(
    token_proxy: CustomToken,
    userdeposit_proxy: UserDeposit,
    orchestrator_address: Address,
    minimum_allowance: TokenAmount,
    maximum_allowance: TokenAmount,
) -> None:
    """Set the allowance of the corresponding smart contract of
    `userdeposit_proxy` to `required_allowance`.
    """
    given_token_address = token_proxy.address
    user_deposit_token_address = userdeposit_proxy.token_address("latest")

    if user_deposit_token_address != given_token_address:
        raise ValueError(
            f"The allowance for the user deposit contract must be increase on the "
            f"corresponding token. Given token: {to_hex(given_token_address)} "
            f"user deposit token: {to_hex(user_deposit_token_address)}."
        )

    current_allowance = token_proxy.allowance(
        orchestrator_address, Address(userdeposit_proxy.address), "latest"
    )

    if minimum_allowance > current_allowance:
        # For the RDN token:
        #
        #     To change the approve amount you first have to reduce the addresses`
        #     allowance to zero by calling `approve(_spender, 0)` if it is not
        #     already 0 to mitigate the race condition described here:
        #     https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
        #
        token_proxy.approve(Address(userdeposit_proxy.address), TokenAmount(0))
        token_proxy.approve(Address(userdeposit_proxy.address), maximum_allowance)


def userdeposit_maybe_deposit(
    userdeposit_proxy: UserDeposit,
    mint_greenlets: Set[Greenlet],
    target_address: Address,
    minimum_effective_deposit: TokenAmount,
    maximum_funding: TokenAmount,
) -> None:
    """Make a deposit at the given `target_address`.

    The amount of tokens depends on the scenario definition's settings.

    If the target address has a sufficient deposit, this is a no-op.

    TODO: Allow setting max funding parameter, similar to the token `funding_min` setting.
    """
    effective_balance = userdeposit_proxy.effective_balance(target_address, "latest")
    current_total_deposit = userdeposit_proxy.get_total_deposit(target_address, "latest")

    if maximum_funding < minimum_effective_deposit:
        raise ValueError(
            f"max_funding must be larger than minimum_effective_deposit, "
            f"otherwise the constraint can never be satisfied. Given "
            f"max_funding={maximum_funding} "
            f"minimum_effective_deposit={minimum_effective_deposit}"
        )

    # Only do a deposit if the current effective balance is bellow the minimum.
    # When doing the deposit, top-up to max_funding to save transactions on the
    # next iterations.
    if effective_balance < minimum_effective_deposit:
        topup_amount = maximum_funding - effective_balance
        new_total_deposit = TokenAmount(current_total_deposit + topup_amount)

        # Wait for mint transactions, if necessary
        gevent.joinall(mint_greenlets, raise_error=True)

        userdeposit_proxy.deposit(
            target_address, new_total_deposit, userdeposit_proxy.client.get_confirmed_blockhash()
        )


def load_token_configuration_from_file(token_file: str) -> TokenDetails:
    """Load token configuration from disk.

    The file contents should be at least::

        {
            "name": "<token name>",
            "address":, "<contract address>",
            "block": <deployment block},
        }

    :raises TokenFileError:
        if the file's contents cannot be loaded using the :mod:`json`
        module, or an expected key is absent.

    :raises TokenInfoFileMissing:
        if the user tries to re-use this token, but no token.info file
        exists for it in the data-path.
    """
    try:
        with open(token_file) as handler:
            token_data = json.load(handler)
    except json.JSONDecodeError as e:
        raise TokenFileError("Token data file corrupted!") from e
    except FileNotFoundError as e:
        raise TokenFileMissing("Token file does not exist!") from e

    if not all(k in token_data for k in ("address", "name", "block")):
        raise TokenFileError("Token data file is missing one or more required keys!")

    return cast(TokenDetails, token_data)


def save_token_configuration_to_file(token_file: str, token_data: TokenDetails) -> None:
    """Save information of the token deployment to a file.

    The file will be JSON encoded and have the following format::

        '{"name": "<token name>", "address": "<contract address>", "block": <deployment block>}'


    """
    with open(token_file) as handler:
        json.dump(token_data, handler)
