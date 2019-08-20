from unittest.mock import patch

import pytest
import requests

from scenario_player.exceptions.services import (
    BrokenService,
    ServiceReadTimeout,
    ServiceUnavailable,
    ServiceUnreachable,
)
from scenario_player.services.utils.interface import ServiceInterface, SPaaSAdapter
from scenario_player.utils.configuration.spaas import SPaaSConfig


@pytest.mark.depends(name="spaas_adapter_mounted")
def test_adapter_is_auto_mounted_in_interface_class():
    iface = ServiceInterface(SPaaSConfig({}))
    assert "spaas" in iface.adapters
    assert isinstance(iface.adapters["spaas"], SPaaSAdapter)


def test_adapter_request_id_is_present_in_interface_automatically():
    iface = ServiceInterface(SPaaSConfig({}))
    assert iface.headers["SP-INSTANCE-ID"] == SPaaSAdapter.REQUEST_ID


@pytest.mark.depends(depends=["spaas_adapter_mounted"])
@patch("scenario_player.services.utils.interface.HTTPAdapter.send")
class TestSPaaSAdapter:
    @pytest.mark.parametrize("service", ["rpc"])
    @pytest.mark.parametrize("port", ["1", None])
    @pytest.mark.parametrize("host", ["superhost.com", None])
    @pytest.mark.parametrize("scheme", ["ftp", None])
    def test_send_loads_host_and_port_correctly(self, _, scheme, host, port, service):
        """If a host and port key have **not** been given in the SPAAS config section,
        SPaaSAdapter.prep_service_request should default to sensible values."""

        expected_url = (
            f"{scheme or 'http'}://{host or '127.0.0.1'}:{port or '5000'}/{service}/my-endpoint"
        )

        input_config = {}
        if host:
            input_config["host"] = host
        if port:
            input_config["port"] = port
        if scheme:
            input_config["scheme"] = scheme

        config = SPaaSConfig({"spaas": {service: input_config}})
        adapter = SPaaSAdapter(spaas_settings=config)

        given_request = requests.Request(url=f"spaas://{service}/my-endpoint").prepare()
        setattr(given_request, "service", service)

        request = adapter.prep_service_request(given_request)
        assert request.url == expected_url

    def test_send_method_monkeypatches_metadata_onto_request(self, mock_adapter_send):
        def return_modded_request(request, *_):
            request.raise_for_status = lambda: True
            request.json = lambda: True
            return request

        mock_adapter_send.side_effect = return_modded_request

        config = SPaaSConfig({"spaas": {}})
        adapter = SPaaSAdapter(config)
        given_request = requests.Request(url="spaas://rpc/my-endpoint").prepare()
        resulting_request = adapter.send(given_request, None)
        assert hasattr(resulting_request, "orig_url")
        assert resulting_request.orig_url == "spaas://rpc/my-endpoint"
        assert hasattr(resulting_request, "service")
        assert resulting_request.service == "rpc"

    @pytest.mark.parametrize(
        "send_err, status_code, expected_err",
        argvalues=[
            (requests.exceptions.ProxyError, None, ServiceUnreachable),
            (requests.exceptions.SSLError, None, ServiceUnreachable),
            (requests.exceptions.ConnectTimeout, None, ServiceUnreachable),
            (requests.exceptions.ReadTimeout, None, ServiceReadTimeout),
            (None, 500, BrokenService),
            (None, 503, ServiceUnavailable),
        ],
        ids=[
            "ProxyError raises ServiceUnreachable",
            "SSLError raises ServiceUnreachable",
            "ConnectTimeout raises ServiceUnreachable",
            "ReadTimeout raises ServiceReadTimeout",
            "500 Internal Server Error raises BrokenService exception",
            "503 Service  raises BrokenService ServiceUnavailable",
        ],
    )
    def test_exceptions_are_converted_correctly_when_expected(
        self, mock_adapter_send, send_err, status_code, expected_err
    ):
        if send_err:
            mock_adapter_send.side_effect = send_err
        else:
            resp = requests.Response()
            resp.status_code = status_code
            mock_adapter_send.return_value = resp

        with pytest.raises(expected_err):
            config = SPaaSConfig({"spaas": {}})
            adapter = SPaaSAdapter(config)
            req = requests.Request(url="http://127.0.0.1:5000").prepare()
            adapter.send(req)

    def test_request_id_is_class_attr(self, _):
        config = SPaaSConfig({"spaas": {}})
        adapter_a = SPaaSAdapter(config)
        adapter_b = SPaaSAdapter(config)
        assert adapter_a.REQUEST_ID == adapter_b.REQUEST_ID
