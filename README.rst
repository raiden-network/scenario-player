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
    (<raiden-venv>) git clone http://github.com/raiden-network/scenario-player
    (<raiden-venv>) cd scenario-player
    (<raiden-venv>) pip install -r requirements .


Usage
-----

Using a ``pip`` installation::

    scenario-player --help

Using ``docker`` (does not require installation via ``pip``)::

    docker run raidennetwork/scenario-player



Scenario Definition
-------------------

.. include:: raiden/scenario_player/scenarios/examples/v2-example-scenario.yaml
    :name: example scenario
