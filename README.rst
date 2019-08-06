.. image:: https://codecov.io/gh/raiden-network/scenario-player/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/raiden-network/scenario-player

Raiden Scenario Player
======================
The Raiden Scneario Player is an integration testing tool written in Python 3. It allows testing of various test scenarios, and is
an integral component in the raiden test suite.

Installation
------------

Using  ``git`` & ``pip``::

    # Clone the raiden repo and install its development version.
    git clone http://github.com/raiden-network/raiden
    cd raiden && make install && cd ..
    # Clone the scenario player repo, and install on the Raiden dev version.
    git clone http://github.com/raiden-network/scenario-player
    cd scenario-player
    pip install ".[dev]"

Usage
-----

Using a ``pip`` installation::

    $ scenario_player --help
    Usage: scenario_player [OPTIONS] COMMAND [ARGS]...

    Options:
      --data-path DIRECTORY           [default: $HOME/.raiden/scenario-player]
      --chain <chain-name>:<eth-node-rpc-url>
                                      Chain name to eth rpc url mapping, multiple allowed
                                      [required]
      --help                          Show this message and exit.

    Commands:
      pack-logs (experimental)
      reclaim-eth
      run

Running a scenario::

    $ scenario-player --chain=goerli:http://geth.goerli.ethnodes.brainbot.com:8545 \

        run --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW} \
        /path/to/scenario.yaml

Reclaiming spent test ether::

    $ scenario-player --chain=goerli:http://geth.goerli.ethnodes.brainbot.com:8545 \
        reclaim-eth --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW}

Scenario Examples
-------------------

For example scenarios have a look at the `raiden` repository's scenarios. These
can be found [here](https://github.com/raiden-network/raiden/tree/develop/raiden/tests/scenarios).
