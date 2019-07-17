from unittest import mock

import pytest


from scenario_player.services.common.blueprints.metrics import metrics_blueprint
from scenario_player.services.utils.factories import construct_flask_app


@pytest.fixture
def client():
    app = construct_flask_app(metrics_blueprint)
    app.config['TESTING'] = True
    client = app.test_client()

    return client


@mock.patch(
    'scenario_player.services.common.blueprints.metrics.generate_latest',
    return_value=b'metrics_generated'
)
def test_metrics_endpoint(_, client):
    response = client.get('/metrics')
    assert response.status_code == 200
