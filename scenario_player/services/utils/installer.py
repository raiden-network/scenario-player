import argparse
import pathlib
import shutil
import subprocess

SERVICE_APPS = {"rpc": "scenario_player.services.rpc.app:RPC_FLASK"}


template = """
[Unit]
Description=Scenario-Player-as-a-Service {service} Unit
After=network.target

[Service]
Type=simple
WorkingDirectory={workdir}
ExecStart={uwsgi} --host {host} --port {port} \"{app_import_path}\"
Restart=always

[Install]
WantedBy=multi-user.target
"""


def installer_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["install", "remove"])
    parser.add_argument(
        "--service",
        choices=list(SERVICE_APPS.keys()),
        default="rpc",
        help="Specify a service to be installed. Installs entire SPaaS stack by default.",
    )
    parser.add_argument(
        "--port",
        default=5100,
        help="Port number to run this service on. Defaults to '5100 + n', where `n` "
             "is the number of already installed services.",
        type=int,
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to run this service on. Defaults to '127.0.0.1'"
    )
    parser.add_argument("--log-service", default=None, help="netloc of a SPaaS Logging Service.")
    parser.add_argument(
        "--raiden-dir",
        default=pathlib.Path.home().joinpath(".raiden"),
        help="Path to the .raiden dir. defaults to ~/.raiden",
        type=pathlib.Path,
    )
    parser.add_argument(
        "--uwsgi",
        type=pathlib.Path,
        default=shutil.which("waitress-serve"),
        help="The UWSGI binary to deploy the service with. Defaults to waitress-serve",
    )
    return parser


def reload_systemd():
    """Invoke `systemctl --user daemon-reload` via a subprocess.
    
    :raises SystemExit: with value 1 if we cannot reload the daemons using systemd.
    """
    print("Reloading Systemd..")
    try:
        subprocess.run("systemctl --user daemon-reload".split(" "), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Could not reload systemd daemons: {e}")
        raise SystemExit(1)
    print("Systemd reloaded.")


def enable_and_start_service(service_fpath):
    """Enable and start a systemd service.
    
    :raises SystemExit: with value 1 if there was an error enabling or starting the service.
    """
    reload_systemd()
    print("Enabling new service..")
    try:
        subprocess.run(f"systemctl --user enable {service_fpath.name}".split(" "), check=True)
        subprocess.run(f"systemctl --user start {service_fpath.name}".split(" "), check=True)
    except subprocess.SubprocessError as e:
        print(f"Failed to enable and start SPaaS Service {service_fpath.name}: {e}")
        raise SystemExit(1)
    print(f"Enabled and started SPaaS Service {service_fpath.name}")


def stop_and_disable_service(service_fpath):
    """Stop and disable a systemd service.

    If `service_fpath` does not exist, we return without error.

    :raises SystemExit: with value 1 if there was an error stopping or disabling the service.
    """
    print("Disabling service..")
    try:
        subprocess.run(f"systemctl --user stop {service_fpath.name}".split(" "), check=True)
        subprocess.run(f"systemctl --user disable {service_fpath.name}".split(" "), check=True)
    except subprocess.CalledProcessError as e:
        if "does not exist" not in (e.stderr or ""):
            print(f"Failed to stop and disable SPaaS Service {service_fpath.name}: {e}")
            raise SystemExit(1)
        print("Service file does not exist, nothing to stop or disable..")
    else:
        print(f"Stopped and disabled SPaaS Service {service_fpath.name}")


def install_service(parsed, service_fpath):
    """Create a new systemd service file at the given `service_fpath`.

    Enables and starts the service if the file was created successfully.

    :raises SystemExit:
        with value 1 if `service_fpath` already exists or the path cannot be written to.
    """
    if service_fpath.exists():
        print(
            f"Service already installed - you must manually remove it or use "
            f"`spaas remove {parsed.service}` to uninstall it."
        )
        raise SystemExit(1)
    print("Creating new user land systemd service..")
    service = template.format(
        service=parsed.service.upper(),
        user=pathlib.Path.home().name,
        workdir=pathlib.Path.home(),
        uwsgi=parsed.uwsgi,
        host=parsed.host,
        port=parsed.port,
        app_import_path=SERVICE_APPS[parsed.service],
    )
    try:
        service_fpath.write_text(service, encoding="UTF-8")
    except Exception as e:
        print(f"Could not write systemd service file at {service_fpath}: {e}")
        raise SystemExit(1)
    print(f"Service file created at {service_fpath}.")
    enable_and_start_service(service_fpath)


def remove_service(parsed, service_fpath):
    """Remove the serivce at the given `service_fpath`.
    
    Stops and disables the service before removing the file.

    If the file does not exist, we carry on.

    Reloads the systemd user daemons before returning.
    """
    stop_and_disable_service(service_fpath)
    print(f"Removing {parsed.service} Service file at {service_fpath}..")
    try:
        service_fpath.unlink()
    except FileNotFoundError:
        print("Service file does not exist, nothing to remove.")
    else:
        print("Service removed.")
    reload_systemd()


def main():
    parser = installer_cli()
    parsed = parser.parse_args()

    user_systemd_dir = pathlib.Path.home().joinpath(".config", "systemd", "user")
    user_systemd_dir.mkdir(exist_ok=True, parents=True)
    service_fpath = user_systemd_dir.joinpath(f"SPaaS-{parsed.service}.service")

    if parsed.command == "install":
        install_service(parsed, service_fpath)
    else:
        remove_service(parsed, service_fpath)
