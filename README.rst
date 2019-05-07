Raiden Scenario Player
======================
The Raiden Scneario Player is an integration testing tool written in Python 3. It allows testing of various test scenarios, and is
an integral component in the raiden test suite.

Installation
------------

Using  `git` & `pip`::

    pip install -e git://git.example.com/MyProject

Usage
-----

Using a `pip` installation::

    scenario-player --help

Using `docker` (does not require installation via `pip`)::

    docker run raidennetwork/scenario-player



Scenario Definition
-------------------

.. include:: raiden/scneario_player/scenarios/examples/v2-example-scenario.yaml
  :tab-width: 2
  :code: yaml
  :name: example scenario
