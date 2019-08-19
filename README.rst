.. image:: https://codecov.io/gh/raiden-network/scenario-player/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/raiden-network/scenario-player

.. image:: https://circleci.com/gh/raiden-network/scenario-player.svg?style=shield
    :target: https://circleci.com/gh/raiden-network/scenario-player

.. image:: https://img.shields.io/docker/cloud/build/raidennetwork/scenario-player
    :alt: Docker Cloud Build Status
    :target: https://cloud.docker.com/u/raidennetwork/repository/docker/raidennetwork/scenario-player/general

.. image:: https://img.shields.io/github/tag-date/raiden-network/scenario-player?label=STABLE
    :target: https://github.com/raiden-network/scenario-player/releases

.. image:: https://img.shields.io/github/license/raiden-network/scenario-player
    :target: https>//github.com/raiden-network/scenario-player

.. image:: https://img.shields.io/github/issues-raw/raiden-network/scenario-player/bug?color=red&label=Open%20Bugs
    :target: https://github.com/raiden-network/scenario-player/issues?q=is%3Aissue+is%3Aopen+label%3Abug

.. image:: https://img.shields.io/github/issues-raw/raiden-network/scenario-player/Feature request?color=orange&label=Open%20Feature%20Requests
    :target: https://github.com/raiden-network/scenario-player/issues?q=is%3Aissue+is%3Aopen+label%3A%22Feature+request%22


Raiden Scenario Player
######################

The Raiden Scenario Player is an integration testing tool written in Python 3. It allows testing of
various scenarios, and is an integral component of the Raiden test suite.

Installation
============

Using  ``git`` & ``pip``::

    # Clone the scenario-player repository
    git clone http://github.com/raiden-network/scenario-player

    # Install Raiden's dev requirements.https://github.com/raiden-network/scenario-player/pull/122
    pip install -r https://raw.githubusercontent.com/raiden-network/raiden/develop/requirements/requirements-dev.txt

    # Install the scenario-player.
    pip install ./scenario-player

Using ``pip``
-------------

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

    $ scenario-player --chain=goerli:http://geth.goerli.ethnodes.brainbot.com:8545 \

        run --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW} \
        /path/to/scenario.yaml

Reclaiming spent test ether::

    $ scenario-player --chain=goerli:http://geth.goerli.ethnodes.brainbot.com:8545 \
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
=================

For example scenarios have a look at the ``Raiden`` repository's scenarios. These
can be found `here <https://github.com/raiden-network/raiden/tree/develop/raiden/tests/scenarios>`_.
