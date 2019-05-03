class TestReleasesHTTPConfig:
    """Test required parameters, status codes and content type of endpoint."""

    def test_GET_returns_json(self, populated_rmc):
        resp = populated_rmc.get('/releases')
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/json'

    def test_GET_returns_json(self, populated_rmc):
        resp = populated_rmc.get('/releases/latest')
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/json'


class TestReleasesEndpoint:

    def test_empty_db(self, release_manager_client):
        resp = release_manager_client.get('/releases')
        assert resp.is_json
        assert not resp.get_json()
        assert resp.status_code == 200

    def test_filter_must_be_in_set_of_predefined_values(self, populated_rmc):
        resp = populated_rmc.get('/releases?filter="nothing"')
        assert reps.status_code == 400
        assert b"'filter' must be one of 'downloaded', 'installed' or 'all'" in resp.get_data()

    def test_GET_returns_dict_of_valid_JSON_release_objects(self, populated_rmc):
        resp = populated_rmc.get('/releases')
        json_data = resp.get_json()
        assert isinstance(json_data, dict)
        assert len(json_data) == 4
        assert all(isinstance(item, dict) for item in json_data.values())
        for item in json_data.values():
            assert 'version' in item
            assert 'archive' in item
            assert isinstance(item['archive'], dict)
            assert 'binary' in item
            assert isinstance(item['binary'], dict)
