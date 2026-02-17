import pytest

from modules.comms.transports import wifi


def test_wifi_requires_base_url(monkeypatch):
    monkeypatch.setattr(wifi.bridge, "AtlasCommandHttpClient", object())

    with pytest.raises(RuntimeError, match="atlas.base_url"):
        wifi.build_wifi_client(base_url="", api_token=None, wifi_config={})
