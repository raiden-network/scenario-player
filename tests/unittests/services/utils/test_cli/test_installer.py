import pathlib
import shutil
import subprocess
from unittest.mock import patch, call, Mock

import pytest

from scenario_player.services.utils.cli.installer import (
    reload_systemd,
    enable_and_start_service,
    stop_and_disable_service,
    install_service,
    remove_service,
    SERVICE_TEMPLATE,
    SERVICE_APPS,
)


@pytest.fixture
def parsed():
    with patch.dict(SERVICE_APPS, {"TEST": "path.to.app"}):
        yield Mock(
            service="TEST", spaas="/bin/ban/bun", host="127.0.0.1", port=5100,
        )


@pytest.fixture
def SERVICE_TEMPLATEd_service(parsed):
    service = SERVICE_TEMPLATE.format(
        service=parsed.service.upper(),
        user=pathlib.Path.home().name,
        workdir=pathlib.Path.home(),
        host=parsed.host,
        port=parsed.port,
        spaas=shutil.which("spaas"),
    )
    return service


@pytest.mark.depends(name="reload_systemd")
@patch("scenario_player.services.utils.cli.installer.subprocess.run", autospec=True)
class TestReloadSystemd:
    def test_func_calls_systemctl_command_with_user_flags(self, mock_run):
        reload_systemd()
        mock_run.assert_called_once_with(["systemctl", "--user", "daemon-reload"], check=True)

    def test_func_raises_systemexit_when_subprocess_fails(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, [""])
        with pytest.raises(SystemExit):
            reload_systemd()


@pytest.mark.depends(name="enable_and_start_service")
@patch("scenario_player.services.utils.cli.installer.subprocess.run", autospec=True)
class TestEnableAndStartService:

    @pytest.mark.parametrize(
        "side_effect",
        argvalues=[
            (None, subprocess.CalledProcessError(1, [""])),
            (subprocess.CalledProcessError(1, [""]), None)
        ],
        ids=("enabling service fails", "starting service fails"),
    )
    def test_func_raises_systemexit_if_process_fails(self, mock_run, side_effect, tmp_path):
        mock_run.side_effect = side_effect

        with pytest.raises(SystemExit):
            enable_and_start_service(tmp_path)

    def test_func_calls_systemd_command_as_expected(self, mock_run, tmp_path):
        enable_and_start_service(tmp_path)
        mock_run.assert_has_calls([call(["systemctl", "--user", "enable", tmp_path.name], check=True), call(["systemctl", "--user", "start", tmp_path.name], check=True)])


@pytest.mark.depends(name="stop_and_disable_service")
@patch("scenario_player.services.utils.cli.installer.subprocess.run", autospec=True)
class TestStopAndDisableService:

    @pytest.mark.parametrize(
        "side_effect",
        argvalues=[
            (None, subprocess.CalledProcessError(1, [""])),
            (subprocess.CalledProcessError(1, [""]), None)
        ],
        ids=("stopping service fails", "disabling service fails"),
    )
    def test_func_raises_systemexit_if_process_fails(self, mock_run, side_effect, tmp_path):
        mock_run.side_effect = side_effect

        with pytest.raises(SystemExit):
            stop_and_disable_service(tmp_path)

    def test_func_does_not_raise_if_process_fails_due_to_missing_service_file(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.CalledProcessError(1, [""], stderr="Service does not exist!")
        stop_and_disable_service(tmp_path)

    def test_func_calls_systemd_command_as_expected(self, mock_run, tmp_path):
        stop_and_disable_service(tmp_path)
        mock_run.assert_has_calls([call(["systemctl", "--user", "stop", tmp_path.name], check=True), call(["systemctl", "--user", "disable", tmp_path.name], check=True)])


@pytest.mark.depends(depends=["stop_and_disable_service", "enable_and_start_service", "reload_systemd"])
class TestInstallService:
    @pytest.fixture(autouse=True)
    def setup_install_service_tests(self):
        with patch("scenario_player.services.utils.cli.installer.enable_and_start_service") as mock_enable_and_start:
            self.mock_enable_and_start = mock_enable_and_start
            yield

    def test_func_calls_path_write_text_at_given_service_fpath(self, parsed, tmp_path, SERVICE_TEMPLATEd_service):
        given_path = tmp_path.joinpath("my.service")
        install_service(parsed, given_path)
        assert given_path.read_text() == SERVICE_TEMPLATEd_service

    def test_func_raises_system_exit_if_service_fpath_exists(self, parsed, tmp_path):
        with pytest.raises(SystemExit):
            install_service(parsed, tmp_path)

    @patch("scenario_player.services.utils.cli.installer.pathlib.Path.write_text", side_effect=Exception)
    def test_func_raises_systemexit_if_it_cannot_write_to_path(self, parsed, tmp_path):
        with pytest.raises(SystemExit):
            install_service(parsed, tmp_path)

    def test_func_call_enable_and_start_service(self, parsed, tmp_path):
        given_path = tmp_path.joinpath("my.service")
        install_service(parsed, given_path)
        self.mock_enable_and_start.assert_called_once_with(given_path)


@pytest.mark.depends(depends=["stop_and_disable_service", "enable_and_start_service", "reload_systemd"])
class TestRemoveService:
    @pytest.fixture(autouse=True)
    def setup_remove_service_tests(self):
        with patch("scenario_player.services.utils.cli.installer.stop_and_disable_service") as mock_stop_and_disable,\
            patch("scenario_player.services.utils.cli.installer.reload_systemd") as mock_reload_systemd,\
            patch("scenario_player.services.utils.cli.installer.pathlib.Path.unlink") as mock_unlink:
            self.mock_unlink = mock_unlink
            self.mock_stop_and_disable = mock_stop_and_disable
            self.mock_reload_systemd = mock_reload_systemd
            yield

    def func_calls_stop_and_disable_service(self, parsed, tmp_path):
        remove_service(parsed, tmp_path)
        self.mock_stop_and_disable.assert_called_once_with(tmp_path)

    def func_calls_unlink_on_given_service_fpath(self, parsed, tmp_path):
        remove_service(parsed, tmp_path)
        self.mock_unlink.assert_called_once_with(tmp_path)

    def func_calls_systemd_reload(self, parsed, tmp_path):
        # TODO: this does not check if this is called last (which it should be).
        remove_service(parsed, tmp_path)
        self.mock_reload_systemd.assert_called_once_with()

    def func_handles_non_existing_service_file_without_raising_an_exception(self, parsed, tmp_path):
        remove_service(parsed, tmp_path.joinpath("does_not.exist"))
