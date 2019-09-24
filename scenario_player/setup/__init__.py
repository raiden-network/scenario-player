"""Scenario Player Setup Utilities.

In order for the scenario player to run a scenario, it must first setup
certain components, in order to be able to execute any tasks stated in a
scenario yaml file.

The following paragraphs will briefly describe the steps that are taken along
the setup phase of a Scenario Player run.

For details, please read the documentation of the respective modules in
:mod:`scenario_player.setup`.


..note::

    Before we continue, we'd like to ensure that some of the less-well defined
    terminology. The following is a list of terms which are used throughout the
    raiden code base, but tend to mean/talk about different things. To ensure
    we do not get lost in translation, here are their definitions as understood
    in this repository:

        Account
        Keystore
        Wallet
            The file holding the ethereum address, which in turn holds funds.

        SP Keystore
        SP Account
            The Keystore file which holds the funds for a scenario. All Raiden
            nodes created for this scenario are funded using this account's ether.
            These funds also pay for Token Contract deployments and RPC calls
            during setup.

        Node Keystore
        Node Account
            The keystore file explicitly created for a node. These are always
            password protected by an empty string and automatically generated
            if they do not exist during setup. Needless to say, it's a terrible
            idea to store actual ether on these.

        Node
        Raiden Client
        Raiden Nodes
            Instances of a `raiden` executable, started with a specific set of
            CLI options.

        SP Token Contract
            The custom token contract deployed or loaded during a scenario run.
            It mints SP Tokens, which are sent between raiden client nodes to
            assert their behaviour's correctness.


Parse and Validate the scenario YAML
====================================

The scenario file is read into memory and loaded using the
tools provided in :mod:`scenario_player.utils.settings`. The latter also validate
the values given for compatibility and correctness, as well as filling in
defaults for absent optional values.


Create Raiden Nodes
===================

Create Keystores
----------------

In this step, we create keystores programmatically for each required Node, as long as
a keystore does not exist already for it.

Construct CLI flags
-------------------
This step constructs the list of command-line flags to pass to the binary. First,
the default/general options are created, and then overriden per node as requested
in the scenario yaml.

Spawn Client in subprocess
--------------------------
Spawn all requested nodes using :mod:`subprocess`. There is no further direct
interaction between the SP and each node's binary after this point.


Ether Funding
=============

SP Account Eth Funding
----------------------
If the SP Account does not have sufficient ether, we cannot do anything useful.
Hence, we check if the SP Account's address has sufficient funding (as defined
in the scenario yaml). If this is **not** the case, we terminate the scenario run,
since we do not, as of now, have any effective way of funding an account on a
test net programmatically.

Raiden Client Node Eth Funding
------------------------------
Next, we check if our Raiden Nodes are sufficiently funded. Since their keystores
are carried over between runs, this may very well be - we typically fund nodes with more
ether than is necessary for a single run, in order to avoid having to fund a
node on *each* run.

If it so happens that funding of the node is sufficient, we skip the funding
step for this particular node. If the balance is lacking, ether is sent from
the SP Account address to the Node's address.

This is repeated for each requested Raiden Node specified in the scenario yaml.


SmartContract Operations
========================

Deploy/Re-use SP Token
----------------------
For our SP to be able to test token transfers, we first need a token to, well, transfer.
By default, the SP deploys a custom token contract to the specified network, which
allows minting tokens via rpc call. This means each run starts with a fresh token economy.

If this is not desired, it's also possible to re-use an existing SP Token ontract.
This must be stated in the scenario yaml, and it must have been created in a previous
SP run.

Raiden Client Nodes Token Funding
---------------------------------
Once the SP Token Contract is deployed or loaded, we can go ahead and fund the
Raiden Client nodes with its tokens. This is done in a similar fashio to eth
funding, in that it "overfunds" them by default, in order to avoid having to fund
them on each run (which wastes time we could instead use to actually run the scenario).

UserDepositContract Token Balance check
---------------------------------------
Next, we check if a UDC is requested in the scenario yaml, and, if so, check the
UDC Token balance of the nodes (as these balances are also persisted between runs).

UserDepositContract Token Allowance Update
------------------------------------------
Depending on the scenario yaml's configuration, we update the allowance of the UDC for our
Test Account address.

Typically, each node would request the UDC tokens themselves, but this would require
setting allowances for each node, resulting in multiple transaction calls (which is something
we would like to avoid, for the sake of reducing set up time).

Instead, we set the allowance for the Test Account, and deposit the tokens from there, into
each of the nodes.

..Note::

    The set `allowance` **must be less than or equal** to the minted amount of
    UDC Tokens! Otherwise, the transactions for these deposits will not succeed,
    due to overstepping the allowed amount.

UserDepositContract Token Deposits
----------------------------------
Once the allowance has been updated, we can mint/deposit UDC Tokens for each of
the nodes. This is done on a per-node basis. As stated before, we deposit more
than necessary by default, in order to avoid having to deposit on each scenario
run.
"""