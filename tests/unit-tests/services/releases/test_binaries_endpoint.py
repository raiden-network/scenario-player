import pathlib
from unittest import mock


from .utils import TestRedis


class TestBinariesHTTPConfig:
    """Test required parameters, status codes and content type of endpoint."""

    def test_GET_returns_json(self, populated_rmc):
        resp = populated_rmc.get('/binaries')
        assert resp.status_code
        assert resp.headers['content-type'] == 'application/json'

    def test_POST_returns_json(self, populated_rmc):
        resp = populated_rmc.post('/binaries', data={'version': '1.0.0'})
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/json'

    def test_POST_requires_version_parameter(self, populated_rmc):
        resp = populated_rmc.post('/binaries')
        assert resp.status_code == 400

    def test_DELETE_returns_204(self, populated_rmc):
        resp = populated_rmc.delete('/binaries?version=1.0.0')
        assert resp.status_code == 204

    def test_DELETE_returns_204_if_version_does_not_exist(self, populated_rmc):
        resp = populated_rmc.delete('/binaries?version=44')
        assert resp.status_code == 204

    def test_DELETE_requires_version_parameter(self, populated_rmc):
        resp = populated_rmc.delete('/binaries')
        assert resp.status_code == 400


@mock.patch('raiden.scenario_player.services.releases.blueprints.binaries.Redis', return_value=TestRedis())
class TestBinariesEndpoint:

    def test_GET_returns_dict_of_valid_binary_JSON_objects(self):
        resp = populated_rmc.get('/binaries')
        json_data = resp.get_json()
        assert isinstance(json_data, dict)
        assert len(json_data) == 2
        assert all(isinstance(item, dict) for item in json_data.values())
        for item in json_data.values():
            assert 'version' in item
            assert 'path' in item
            assert isinstance(item['path'], str)
            assert 'bin_path' in item
            assert isinstance(item['archive_path'], str)

    def test_POST_returns_valid_binary_JSON_object(self):
        # Install a new release binary.
        resp = populated_rmc.post('/binaries', data={'version': RELEASE_NO_ARCHIVE_NO_BIN})
        json_data = resp.get_json()
        assert resp.status_code == 200

        # Check the layout.
        assert isinstance(json_data, dict)
        assert len(json_data) == 3

        assert 'version' in json_data
        assert isinstance(json_data['version'], str)

        assert 'path' in json_data
        assert isinstance(json_data['path'], str)

        assert 'bin_path' in json_data
        assert isinstance(json_data['archive_path'], str)

    def test_POST_binary_object_returned_has_the_expected_values(self, populated_rmc):
        # Download a new release's archive.
        version = RELEASE_NO_ARCHIVE_NO_BIN
        resp = populated_rmc.post('/binaries', data={'version': version})
        json_data = resp.get_json()
        assert resp.status_code == 200

        # Check the content
        archive_fname = f'{version}.tar.gz'
        expected_archive_path = pathlib.Path(populated_rmc.app.config['DOWNLOAD_DIR']).joinpath(archive_fname)
        expected_bin_path = pathlib.Path(populated_rmc.application.config['BIN_DIR']).joinpath(version)
        assert json_data['version'] == '2.0.0'
        assert json_data['path'] == str(expected_bin_path)
        assert json_data['archive_path'] == str(expected_archive_path)

    def test_POST_requires_version_parameter(self, populated_rmc):
        resp = populated_rmc.post('/binaries')
        assert resp.status_code == 400
        assert b'version' in resp.get_data()

    def test_POST_downloads_archive_before_installing_if_it_is_not_available_locally(self, populated_rmc):
        version = RELEASE_NO_ARCHIVE_NO_BIN
        archive_fname = f'{version}.tar.gz'
        expected_archive_path = pathlib.Path(populated_rmc.application.config['DOWNLOAD_DIR']).joinpath(archive_fname)

        assert expected_archive_path.exists() is False

        resp = populated_rmc.post('/binaries', data={'version': version})
        assert resp.status_code == 200

        assert expected_archive_path.exists() is True

    def test_POST_skips_archive_download_if_its_available_locally(self, populated_rmc):
        pytest.fail('Not Implemented!')

    def test_DELETE_without_purge_removes_only_binary_from_machine(self, populated_rmc):
        version = RELEASE_WITH_ARCHIVE_AND_BIN
        archive_fname = f'{version}.tar.gz'
        archive_path = pathlib.Path(populated_rmc.application.config['DOWNLOAD_DIR']).joinpath(archive_fname)
        bin_path = pathlib.Path(populated_rmc.application.config['BIN_DIR']).joinpath(version)
        assert archive_path.exists() is True
        assert bin_path.exists() is True

        resp = populated_rmc.delete(f'/binaries?{version}')
        assert resp.status_code == 204

        assert archive_path.exists() is True
        assert bin_path.exists() is False

    def test_DELETE_with_purge_removes_binary_and_archive_from_machine(self, populated_rmc):
        version = RELEASE_WITH_ARCHIVE_AND_BIN
        archive_fname = f'{version}.tar.gz'
        archive_path = pathlib.Path(populated_rmc.application.config['DOWNLOAD_DIR']).joinpath(archive_fname)
        bin_path = pathlib.Path(populated_rmc.application.config['BIN_DIR']).joinpath(version)
        assert archive_path.exists() is True
        assert bin_path.exists() is True

        resp = populated_rmc.delete(f'/binaries?{version}&purge=true')
        assert resp.status_code == 204

        assert archive_path.exists() is False
        assert bin_path.exists() is False

    def test_DELETE_knows_how_to_handle_purge_parameter_conversion(self, populated_rmc):
        pytest.fail('Not implemented!')
