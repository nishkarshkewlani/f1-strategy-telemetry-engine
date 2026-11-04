"""Unit tests for OpenF1 API Client."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests

from ingestion.api_client import OpenF1Client


def test_client_init_and_cache_dir(tmp_path):
    client = OpenF1Client(cache_dir=tmp_path)
    assert client.cache_dir == tmp_path
    assert tmp_path.exists()


@patch("requests.Session.get")
def test_client_get_success(mock_get, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"session_key": 9158, "session_name": "Race"}]
    mock_get.return_value = mock_response

    client = OpenF1Client(cache_dir=tmp_path)
    data = client.get("sessions", params={"year": 2023}, use_cache=True)

    assert len(data) == 1
    assert data[0]["session_key"] == 9158
    # Assert cache file was created
    cached_files = list(tmp_path.glob("*.json"))
    assert len(cached_files) == 1


def test_client_uses_existing_cache(tmp_path):
    cached_payload = [{"session_key": 9999, "session_name": "Test Race"}]
    cache_file = tmp_path / "sessions_test.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cached_payload, f)

    client = OpenF1Client(cache_dir=tmp_path)
    # Even without mocking requests, it loads directly from cache
    data = client.get("sessions", use_cache=True, cache_filename="sessions_test.json")
    assert len(data) == 1
    assert data[0]["session_key"] == 9999


@patch("requests.Session.get")
def test_client_http_error(mock_get, tmp_path):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
    mock_get.return_value = mock_response

    client = OpenF1Client(cache_dir=tmp_path)
    with pytest.raises(requests.exceptions.HTTPError):
        client.get("unknown_endpoint", use_cache=False)
