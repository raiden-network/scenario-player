import argparse
import pathlib
import shutil
import subprocess


from scenario_player.services.utils.cli.constants import SERVICE_TEMPLATE, SERVICE_APPS


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
    service = SERVICE_TEMPLATE.format(
        service=parsed.service,
        user=pathlib.Path.home().name,
        workdir=pathlib.Path.home(),
        spaas=shutil.which("spaas"),
        host=parsed.host,
        port=parsed.port,
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


def install_command(parsed):
    """Install or remove a SPaaS Systemd Service."""
    user_systemd_dir = pathlib.Path.home().joinpath(".config", "systemd", "user")
    user_systemd_dir.mkdir(exist_ok=True, parents=True)
    service_fpath = user_systemd_dir.joinpath(f"SPaaS-{parsed.service}.service")

    if parsed.command == "install":
        install_service(parsed, service_fpath)
    else:
        remove_service(parsed, service_fpath)
