import hashlib
import json
import platform
import re
import sys
from unittest.mock import patch

import pytest
import responses
from eth_utils import encode_hex, to_checksum_address

from scenario_player.exceptions.setup import ArchiveNotFound
from scenario_player.setup.nodes.utils import get_local_seed, create_keystore, RaidenExecutable
from scenario_player.utils.files.constants import CLOUD_STORAGE_URL
from scenario_player.utils.files.base import ManagedFile


ANY_CLOUD_URL = re.compile(f"^{CLOUD_STORAGE_URL}.*")


@pytest.fixture
def local_seed(tmp_path):
    return get_local_seed(tmp_path)


@pytest.fixture
def mock_archive(tmp_path):
    mock_archive = tmp_path.joinpath("test.archive")
    mock_archive.touch()
    mock_archive.write_text("test data")
    return mock_archive


@pytest.fixture
def create_keystore_params():
    return {"name": "my_scenario", "run_number": 6, "index": 1, "password": ""}


class TestGetLocalSeed:
    @patch("scenario_player.setup.nodes.utils.random.randint", return_value=1)
    def test_func_generates_seed_as_expected(self, mock_randint, tmp_path):
        """The seed is a hex-encoded byte sequence of 20 randomly chosen integers in range of 0-255."""
        expected = encode_hex(bytes(1 for _ in range(20)))
        assert get_local_seed(tmp_path) == expected
        assert mock_randint.call_count == 20

    def test_func_generates_file_on_expected_path(self, dummy_scenario_runner, tmp_path):
        """Ensure :func:``local_seed``creates the seed file inside the ``base_path``."""
        seed_file = tmp_path.joinpath("seed.txt")

        assert not seed_file.exists()

        seed = get_local_seed(tmp_path)

        assert seed_file.exists()
        assert seed == seed_file.read_text().strip()


class TestCreateKeystore:
    def test_file_holds_values_as_json_encoded_utf_8_string(self, create_keystore_params):
        keystore_file = create_keystore(**create_keystore_params)
        try:
            json.loads(keystore_file.read_text(encoding="UTF-8"))
        except UnicodeDecodeError:
            pytest.fail("String is not UTF-8 encoded")
        except json.JSONDecodeError:
            pytest.fail("File does not hold a valid JSON string!")

    def test_resulting_path_has_expected_filename(self, create_keystore_params):
        """The file name is matches `<checksum of eth_address>.keystore`."""
        keystore_file = create_keystore(**create_keystore_params)
        data = json.loads(keystore_file.read_text())
        address = data["address"]
        assert keystore_file.stem == to_checksum_address(address)
        assert keystore_file.suffix == "keystore"

    @patch("scenario_player.setup.nodes.utils.create_keyfile_json")
    def test_generated_private_key_is_sha256_hash_of_func_parameters(self, mock_create_json, local_seed, runner):
        """The private key is a hashed str using sha256.

        The original string is a combination of the local seed, the run number,
        the instance's index, and the scenario name.
        """
        name = "my_scenario"
        run_number = 6
        index = 1
        seed = (
            f"{local_seed}"
            f"-{name}"
            f"-{run_number}"
            f"-{index}"
        ).encode()
        expected = hashlib.sha256(seed).digest()

        create_keystore(run_number=run_number, index=index, scenario_name=name, password="")
        mock_create_json.assert_called_once_with(expected, b"")


class TestRaidenExecutable:

    @responses.activate
    def test_download_returns_managedfile_instance(self, tmp_path, mock_archive):
        version = "1.0.0"
        responses.add(
            responses.GET,
            url=ANY_CLOUD_URL,
            status=200,
            stream=True,
            content_type="application/octet-stream",
            body=mock_archive.read_bytes()
        )
        dloaded_file = RaidenExecutable.download(version, tmp_path)
        assert isinstance(dloaded_file, ManagedFile)

    def test_download_raises_exception_if_request_returns_404(self, tmp_path):
        version = "non-existing"
        with pytest.raises(ArchiveNotFound):
            RaidenExecutable.download(version, tmp_path)

    @patch("scenario_player.setup.nodes.utils.requests.get")
    def test_download_requests_file_from_raiden_cloud(self, mock_get):
        version = "666.666.666"
        RaidenExecutable.download(version, tmp_path)
        args, kwargs = mock_get.call_args
        url, *_ = args
        assert CLOUD_STORAGE_URL in url

    @responses.activate
    def test_download_stores_downloaded_file_in_expected_directory(self, tmp_path, mock_archive):
        responses.add(
            responses.GET,
            url=ANY_CLOUD_URL,
            status=200,
            stream=True,
            content_type="application/octet-stream",
            body=mock_archive.read_bytes()
        )
        version = "1.0.0"
        expected = f"v{version}_{sys.platform}_{platform.machine()}.tar.gz"
        dloaded_file = RaidenExecutable.download(version, tmp_path)
        assert tmp_path.joinpath(expected).exists()
        assert tmp_path.joinpath(expected) == dloaded_file.path

    @patch("scenario_player.setup.nodes.utils.requests.get")
    def test_download_factors_in_platform_and_architecture_when_generating_the_version_to_download(self, mock_get, tmp_path):
        version = "666.666.666"
        RaidenExecutable.download(version, tmp_path)
        args, kwargs = mock_get.call_args
        url, *_ = args
        assert f"v{version}_{sys.platform}_{platform.machine()}.tar.gz" in url
        mock_get.assert_called_once_with(f"{CLOUD_STORAGE_URL}/")

    @responses.activate
    def test_download_is_idempotent(self, mock_archive, tmp_path):
        """Calling :meth:`RaidenExecutable.download()` several times downloads the file only once."""
        responses.add(
            responses.GET,
            url=ANY_CLOUD_URL,
            status=200,
            stream=True,
            content_type="application/octet-stream",
            body=mock_archive.read_bytes()
        )
        version = "1.0.0"
        RaidenExecutable.download(version, tmp_path)
        RaidenExecutable.download(version, tmp_path)
        RaidenExecutable.download(version, tmp_path)
        assert len(responses.calls) == 1

    @pytest.mark.parametrize("platform", ["linux", "darwin"])
    @responses.activate
    @patch("scenario_player.setup.nodes.utils.tarfile.Tarfile.extractall")
    @patch("scenario_player.setup.nodes.utils.zipfile.Zipfile.extractall")
    def test_unpack_extracts_archive_file_in_same_folder_as_archive(self, mock_zip, mock_tar, platform, mock_archive, tmp_path):
        responses.add(
            responses.GET,
            url=ANY_CLOUD_URL,
            status=200,
            stream=True,
            content_type="application/octet-stream",
            body=mock_archive.read_bytes()
        )
        version = "1.0.0"
        expected = f"v{version}_{platform}_{platform.machine()}"
        archive = RaidenExecutable.download(version, tmp_path)
        unpacked = archive.unpack()

        assert unpacked.path.parent == archive.path.parent
        assert unpacked.path.name == expected

        if platform == "linux":
            mock_tar.assert_called_once_with(tmp_path)
        else:
            mock_zip.assert_called_once_with(tmp_path)


