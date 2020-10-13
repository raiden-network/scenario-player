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

    # Show available commands:
    ~/ $scenario_player --help

    # Show help for subcommand, e.g.:
    ~/ $scenario_player run --help


You can also use `make`::

    make install


For Developers
--------------

`make` is your friend::

    make install-dev

Note that this installs a pypi version of `raiden` - if you'd like to run the SP against the latest
commit on the `develop` branch of the `raiden` repository, addtionally run this command::

    make install-raiden-develop

For all other versions of `raiden`, you will have to manually install it.


Usage
=====

Invoking the `scenario-player` from the cli can be done in one of the following
ways, depending on how you installed the tool.

Invoke the command directly on the cli::

    $ scenario-player run \
        --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW} \
        /path/to/scenario.yaml

Reclaiming spent test ether::

    $ scenario-player reclaim --chain=goerli:http://geth.goerli.ethnodes.brainbot.com:8545 \
        --keystore-file=/path/to/keystore.file --password=${KEYSTORE_PW}


Scenario Examples
=================

For example scenarios have a look at the ``Raiden`` repository's scenarios. These
can be found `here <https://github.com/raiden-network/raiden/tree/develop/raiden/tests/scenarios>`_.

Tools
=================
With the `Performance Analysis Tool <https://github.com/raiden-network/performance-analysis-tool>`_
the logs of the scenario player can be analyzed and visualized.
