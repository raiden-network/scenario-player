.. image:: https://codecov.io/gh/raiden-network/scenario-player/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/raiden-network/scenario-player

Raiden Scenario Player
======================
The Raiden Scenario Player is an integration testing tool written in Python 3. It allows testing of various test scenarios, and is
an integral component in the raiden test suite.

Installation
------------

Using  ``git`` & ``pip``::

    # Clone the scenario-player repository
    git clone http://github.com/raiden-network/scenario-player

    # Install raiden's dev requirements.https://github.com/raiden-network/scenario-player/pull/122
    pip install -r https://raw.githubusercontent.com/raiden-network/raiden/develop/requirements/requirements-dev.txt

    # Install the scenario-player.
    pip install ./scenario-player

Using ``pip``
-------------

Using a ``pip`` installation::

    $ scenario-player --help
    Usage: scenario-player [OPTIONS] COMMAND [ARGS]...

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


Using ``docker``
----------------
Pulling an image is as simple as::

    docker pull raidennetwork/scenario-player:<tag>

Where ``<tag>`` may be a specific version, git branch or ``latest`` for the last commit
on ``dev``, or ``stable`` for the last release on ``master``.


Usage
=====

Invoking the `scenario-player` from the cli can be done in one of the following
ways, depending on how you installed the tool.

``pip`` installation
--------------------
Invoke the command directly on the cli::

    $ ${SP} --chain=goerli:http:geth.goerli.ethnodes.brainbot.com:8545 \
        run --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW} \
        /path/to/scenario.yaml

Reclaiming spent test ether::

    $ scenario-player --chain=goerli:http:geth.goerli.ethnodes.brainbot.com:8545 \
        reclaim-eth --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW}

`docker` image
--------------

If you're using docker, replace the ``scenario-player`` command with a ``docker run`` command, like so::

    docker run -i -t \
       -v ${DATA_DIR}:/data \
       -v ${WALLET_DIR}:${WALLET_DIR}:ro \
       raidennetwork/scenario-player:${branch}

As you can see, you'll have to mount some local directories to the container, otherwise
the container will not run. ``DATA_DIR`` is the location of your blockchain data,
and the ``WALLET_DIR`` should point to the location of your wallet file.

Scenario Examples
-------------------

For example scenarios have a look at the ``raiden`` repository's scenarios. These
can be found `here <https://github.com/raiden-network/raiden/tree/develop/raiden/tests/scenarios>`_.
