"""Microservice managing RPC client instances for the Scenario Player.

As scenarios are run in parallel, there must exist a single instance
managing transactions, as otherwise the underliying JSONRPC client
cannot correctly manage and increase nonce values.

This service takes care of this problem.

It initializes and manages a JSONRPC instance internally, offering
a simple REST API to send transactions, as well as deploying token contracts and
minting their tokens. Finally, it allows updating the allowance of a User Deposit Contract.

In order to use the service, a user must first request a `client_id` for the desired
JSONRPCClient configuration combination::

    POST /rpc/instance

        {"gas_price": "fast", "chain_url": "http://test.net:8545", "privkey": "my_private_key"}

This will return a JSON response with a single key, `client_id`:

    200 OK

        {"client_id": "<rpc-client-id>"}

This operation is idempotent, and will not create multiple instances if called repeatedly -
instead, it will always return the same instance for a configuration combination / `client_id`.

For all other requests to the RPC service, the `client_id` must be passed along in the query.

Deploying a Token will looks like this::

    POST /rpc/token

        {
            "client_id": <str>,
            "constructor_args": {
                "decimals": <int>,
                "name": <str>,
                "symbol": <str>,
            }
        }

    200 OK

        {
            "deployment_block": <int>,
            "address": <str>,
        }

Minting tokens and setting the allowance for an UDC looks like this::

    POST /rpc/contract/mint
    POST /rpc/contract/allowance

        {
            "client_id": <str>,
            "target_address": <str>,
            "contract_address": <str>,
            "gas_limit": <int>,
            "amount": <float>,
        }

    200 OK

        {
            "tx_hash": <str>,
        }

Should you ever be in the need of deleting an instance, this can be done like so::

    DELETE /rpc/instance?client_id=<str>

    204 No Content

.. Note::

    This endpoint always returns `204`, regardless of whether or not the instance
    actually existed.

"""
