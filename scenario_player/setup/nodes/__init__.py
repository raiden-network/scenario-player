"""Raiden Client Node configuration utilities.

Usage::

    scenario_yaml = ScenarioYaml(yaml_path= ... , data_path= ...)
    procs_and_configs = []
    for i in range(scenario_yaml.nodes.count):
        node_config = RaidenConfig(scenario_yaml, index=i, chain="goerli", client_addr="geth.goerli.ethnodes.brainbot.com")
        command = node_config.as_cli_command()
        proc = RaidenClientExecutor(command, node_config.ip_address + "/api/v1/address")
        proc.start()
        procs_and_configs.append([proc, config])
"""