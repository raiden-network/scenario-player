from unittest import mock

import pytest


from scenario_player.services.common.blueprints import metrics_view
from scenario_player.services.common.factories import construct_flask_app

@pytest.fixture
def client():
    app = construct_flask_app(metrics_view)
    app.config['TESTING'] = True
    client = app.test_client()

    return client


@mock.patch('scenario_player.services.common.blueprints.generate_latest', return_value=b'metrics_generated')
def test_metrics_endpoint(mock_generate_metrics, client):
    response = client.get('/metrics')
    assert response.status_code == 200
