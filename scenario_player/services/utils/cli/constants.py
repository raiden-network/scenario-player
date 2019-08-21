import scenario_player.services.rpc.app


SERVICE_APPS = {"rpc": scenario_player.services.rpc.app.serve}

SERVICE_TEMPLATE = """
[Unit]
Description=Scenario-Player-as-a-Service {service} Unit
After=network.target

[Service]
Type=simple
WorkingDirectory={workdir}
ExecStart={spaas} start --service {service} --host {host} --port {port}
Restart=always

StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=SPaaS-{service}

[Install]
WantedBy=multi-user.target
"""