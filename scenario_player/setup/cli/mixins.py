import argparse
import pathlib

#: CLI flags to state a keystore and its password.
account_options = argparse.ArgumentParser(add_help=False)
account_options.add_argument("--keystore", required=True, nargs=1, type=pathlib.Path)
account_options.add_argument(
    "--keystore-pw",
    required=True,
    type=pathlib.Path,
    nargs=1,
    help="String, file or pipe input used to unlock the given keystore.",
)

#: CLI flags allowing configuration of the network and Ethereum client rpc address
network_options = argparse.ArgumentParser(add_help=False)
network_options.add_argument(
    "--network", required=True, nargs=1, help="The name of the blockchain network to use."
)
network_options.add_argument(
    "--rpc-address", required=True, nargs=1, help="RPC Address of the Ethereum client to use."
)
