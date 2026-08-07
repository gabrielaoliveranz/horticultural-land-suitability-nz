# =============================================================================
# TERROIR — Unit tests for api_retry.py
# Script: tests/test_api_retry.py
# Stage:  Testing
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Covers src/api_retry.py's get_with_retry() using unittest.mock to patch
requests.get and time.sleep — no real network calls, no real waiting.
"""

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
import requests

from api_retry import get_with_retry


def make_response(
    status_code: int, retry_after: Optional[str] = None
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.headers = (
        {"Retry-After": retry_after} if retry_after is not None else {}
    )
    if status_code >= 400:
        response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError(f"{status_code} error")
        )
    else:
        response.raise_for_status.return_value = None
    return response


@patch("api_retry.time.sleep")
@patch("api_retry.requests.get")
def test_200_returns_immediately_with_no_retry(
    mock_get: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_get.return_value = make_response(200)

    response = get_with_retry("http://example.test")

    assert response.status_code == 200
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


@patch("api_retry.time.sleep")
@patch("api_retry.requests.get")
def test_500_then_200_retries_once_and_succeeds(
    mock_get: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_get.side_effect = [make_response(500), make_response(200)]

    response = get_with_retry("http://example.test")

    assert response.status_code == 200
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


@patch("api_retry.time.sleep")
@patch("api_retry.requests.get")
def test_404_raises_immediately_and_is_never_retried(
    mock_get: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_get.return_value = make_response(404)

    with pytest.raises(requests.exceptions.HTTPError):
        get_with_retry("http://example.test")

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


@patch("api_retry.time.sleep")
@patch("api_retry.requests.get")
def test_persistent_503_stops_after_max_retries_and_raises(
    mock_get: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_get.return_value = make_response(503)

    with pytest.raises(requests.exceptions.HTTPError):
        get_with_retry("http://example.test", max_retries=2)

    # 1 initial attempt + 2 retries = 3 calls; sleeps before each retry.
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


@patch("api_retry.time.sleep")
@patch("api_retry.requests.get")
def test_numeric_retry_after_is_honoured_over_backoff(
    mock_get: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_get.side_effect = [
        make_response(429, retry_after="5"),
        make_response(200),
    ]

    response = get_with_retry(
        "http://example.test", backoff_base_seconds=1.0
    )

    assert response.status_code == 200
    mock_sleep.assert_called_once_with(5.0)


@patch("api_retry.time.sleep")
@patch("api_retry.requests.get")
def test_malformed_retry_after_falls_back_to_backoff(
    mock_get: MagicMock, mock_sleep: MagicMock
) -> None:
    mock_get.side_effect = [
        make_response(429, retry_after="not-a-number"),
        make_response(200),
    ]

    response = get_with_retry(
        "http://example.test", backoff_base_seconds=1.0
    )

    assert response.status_code == 200
    # attempt=1 -> backoff_base_seconds * 2**(1-1) = 1.0
    mock_sleep.assert_called_once_with(1.0)
