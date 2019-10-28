.. image:: https://codecov.io/gh/raiden-network/scenario-player/branch/master/graph/badge.svg
    :alt: Code Coverage
    :target: https://codecov.io/gh/raiden-network/scenario-player

.. image:: https://circleci.com/gh/raiden-network/scenario-player.svg?style=shield
    :alt: CI Status
    :target: https://circleci.com/gh/raiden-network/scenario-player

.. image:: https://img.shields.io/docker/cloud/build/raidennetwork/scenario-player
    :alt: Docker Cloud
    :target: https://cloud.docker.com/u/raidennetwork/repository/docker/raidennetwork/scenario-player/general

.. image:: https://img.shields.io/github/tag-date/raiden-network/scenario-player?label=STABLE
    :alt: Releases
    :target: https://github.com/raiden-network/scenario-player/releases

.. image:: https://img.shields.io/github/license/raiden-network/scenario-player
    :alt: License
    :target: https>//github.com/raiden-network/scenario-player

.. image:: https://img.shields.io/github/issues-raw/raiden-network/scenario-player/bug?color=red&label=Open%20Bugs
    :alt: Open Bugs
    :target: https://github.com/raiden-network/scenario-player/issues?q=is%3Aissue+is%3Aopen+label%3Abug


######################
Raiden Scenario Player
######################

The Raiden Scenario Player is an integration testing tool written in Python 3. It allows testing of
various scenarios, and is an integral component of the Raiden test suite.

Installation
============

For Users
---------

Using  ``git`` & ``pip``::

    # Clone the scenario-player repository
    ~/ $git clone http://github.com/raiden-network/scenario-player

    # Install the scenario-player.
    ~/ $pip install ./scenario-player

    ~/ $scenario_player --help
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


You can also use `make`::

    make install


Or docker::

    docker pull raidennetwork/scenario-player:<tag>

Where ``<tag>`` may be a specific version, git branch or ``latest`` for the last commit
on ``dev``, or ``stable`` for the last release on ``master``.


For Developers
--------------

`make` is your friend::

    make install-dev

Note that this installs a pypi version - if you'd like to run the SP against the latest
commit on the `develop` branch of the `raiden` repository, addtionally run this command::

    make install-raiden-develop

For all other versions of `raiden`, you will have to manually install it.


Usage
=====

Invoking the `scenario-player` from the cli can be done in one of the following
ways, depending on how you installed the tool.

Invoke the command directly on the cli::

    $ scenario-player --chain=goerli:http://geth.goerli.ethnodes.brainbot.com:8545 \

        run --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW} \
        /path/to/scenario.yaml

Reclaiming spent test ether::

    $ scenario-player --chain=goerli:http://geth.goerli.ethnodes.brainbot.com:8545 \
        reclaim-eth --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW}


If you're using docker, use the ``docker run`` command, like so::

    docker run -i -t \
       -v ${DATA_DIR}:/data \
       -v ${WALLET_DIR}:${WALLET_DIR}:ro \
       raidennetwork/scenario-player:${branch}

As you can see, you'll have to mount some local directories to the container, otherwise
the container will not run. ``DATA_DIR`` is the location of your blockchain data,
and the ``WALLET_DIR`` should point to the location of your wallet file.

Scenario Examples
=================

For example scenarios have a look at the ``Raiden`` repository's scenarios. These
can be found `here <https://github.com/raiden-network/raiden/tree/develop/raiden/tests/scenarios>`_.

Tools
=================
With the `performance analysis <https://github.com/raiden-network/performance-analysis-tool>`_ 
tool the logs of the scenario player can be analyzed and visualized.