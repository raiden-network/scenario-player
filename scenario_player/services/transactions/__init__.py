"""Microservice managing transactions for the Scenario Player.

As scenarios are run in parallel, there must exist a single instance
managing transactions, as otherwise the underliying JSONRPC client
cannot correctly manage and increase nonce values.

This service takes care of this problem.

It initializes and manages a JSONRPC instance internally, offering
a simple REST API to send and track transactions, as well as
deploying token contracts and minting their tokens.
"""
