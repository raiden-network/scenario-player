import pathlib
from unittest import mock


from .utils import TestRedis


class TestArchivesHTTPConfig:
    """Test required parameters, status codes and content type of endpoint."""

    def test_GET_returns_json(self, populated_rmc):
        resp = populated_rmc.get('/archives')
        assert resp.status_code
        assert resp.headers['content-type'] == 'application/json'

    def test_POST_returns_json(self, populated_rmc):
        resp = populated_rmc.post('/archives', data={'version': '1.0.0'})
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/json'

    def test_POST_requires_version_parameter(self, populated_rmc):
        resp = populated_rmc.post('/archives')
        assert resp.status_code == 400

    def test_DELETE_returns_204(self, populated_rmc):
        resp = populated_rmc.delete('/archives?version=1.0.0')
        assert resp.status_code == 204

    def test_DELETE_returns_204_if_version_does_not_exist(self, populated_rmc):
        resp = populated_rmc.delete('/archives?version=44')
        assert resp.status_code == 204

    def test_DELETE_requires_version_parameter(self, populated_rmc):
        resp = populated_rmc.delete('/archives')
        assert resp.status_code == 400


@mock.patch('raiden.scenario_player.services.releases.blueprints.archives.Redis', return_value=TestRedis())
class TestArchivesEndpoint:

    def setup_method(self):
        """Populate the database.

        The following are required:

            - A Release without local archive and binary
            - A Release with a local archive and no local binary
            - A Release with a local archive and binary
            - A Release without a local archive and a local binary
        """

    def test_GET_returns_dict_of_valid_archive_JSON_objects(self, mock_redis, populated_rmc):
        resp = populated_rmc.get('/archives')
        json_data = resp.get_json()
        assert isinstance(json_data, dict)
        assert len(json_data) == 4
        assert all(isinstance(item, dict) for item in json_data.values())
        for item in json_data.values():
            assert 'version' in item
            assert 'path' in item
            assert isinstance(item['path'], str)
            assert 'bin_path' in item
            assert isinstance(item['bin_path'], str)

    def test_POST_downloads_the_release_and_returns_valid_archive_JSON_object(self, mock_redis, populated_rmc):
        # Download a new release's archive.
        resp = populated_rmc.post('/archives', data={'version': RELEASE_NO_ARCHIVE_NO_BIN})
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
        assert isinstance(json_data['bin_path'], str)

    def test_POST_archive_object_returned_has_expected_values(self, mock_redis, populated_rmc):
        # Download a new release's archive.
        version = RELEASE_NO_ARCHIVE_NO_BIN
        resp = populated_rmc.post('/archives', data={'version': version})
        json_data = resp.get_json()
        assert resp.status_code == 200

        # Check the content
        expected_archive_path = pathlib.Path(populated_rmc.application.config['DOWNLOAD_DIR']).joinpath(f'{version}.tar.gz')
        assert json_data['version'] == version
        assert json_data['path'] == str(expected_archive_path)
        assert json_data['bin_path'] == ''

    def test_POST_requires_version_parameter(self, mock_redis, populated_rmc):
        resp = populated_rmc.post('/archives')
        assert resp.status_code == 400
        assert b'version' in resp.get_data()

    def test_POST_requesting_unknown_version_returns_400(self, populated_rmc):
        resp = populated_rmc.post('/archives', data={'version': '3.0.0'})
        assert resp.status_code == 400
        assert b'Invalid version' in resp.get_data()

    def test_DELETE_removes_archive_from_machine(self, populated_rmc):
        resp = populated_rmc.delete(f'/archives?version={RELEASE_WITH_ARCHIVE_NO_BIN}')
        assert resp.status_code == 204
        assert resp.get_data() is None

        # Assert file no longer exists
        archive_fname = f'{RELEASE_WITH_ARCHIVE_NO_BIN}.tar.gz'
        archive_path = pathlib.Path(populated_rmc.application.config['DOWNLOAD_DIR']).joinpath(archive_fname)
        assert archive_path.exists() is False

    def test_DELETE_throws_400_if_version_param_is_missing(self, populated_rmc):
        resp = populated_rmc.delete('/archives')
        assert resp.status_code == 400
        assert b'version' in resp.get_data()
