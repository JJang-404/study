"""robust_client.py 단위 테스트 — sleep은 mock으로 대체."""

import sys
import os
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from robust_client import ApiCallError, call_api


def _make_response(status_code: int, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    return resp


# ── 케이스 1: 2회 5xx 실패 후 3회차 200 성공 ─────────────────────────────
@patch("robust_client.time.sleep")
@patch("robust_client.requests.request")
def test_retry_on_5xx_then_success(mock_req, mock_sleep):
    mock_req.side_effect = [
        _make_response(500),
        _make_response(503),
        _make_response(200, {"result": "ok"}),
    ]

    result = call_api("http://example.com/api")

    assert result == {"result": "ok"}
    assert mock_req.call_count == 3
    assert mock_sleep.call_count == 2  # 2회 대기 후 3회차 성공


# ── 케이스 2: 3회 모두 타임아웃 → ApiCallError ───────────────────────────
@patch("robust_client.time.sleep")
@patch("robust_client.requests.request")
def test_all_timeout_raises_error(mock_req, mock_sleep):
    from requests.exceptions import ReadTimeout

    mock_req.side_effect = [ReadTimeout(), ReadTimeout(), ReadTimeout()]

    with pytest.raises(ApiCallError):
        call_api("http://example.com/api", max_retries=3)

    assert mock_req.call_count == 3
    assert mock_sleep.call_count == 2  # 마지막 시도 후엔 sleep 없음


# ── 케이스 3: 404 → 재시도 없이 즉시 예외 ────────────────────────────────
@patch("robust_client.time.sleep")
@patch("robust_client.requests.request")
def test_404_raises_immediately_no_retry(mock_req, mock_sleep):
    mock_req.return_value = _make_response(404)

    with pytest.raises(ApiCallError):
        call_api("http://example.com/api")

    assert mock_req.call_count == 1  # 단 1회만 호출
    mock_sleep.assert_not_called()  # 대기 없음


# ── 케이스 4: 429 + Retry-After=2 → 지정 지연 후 재시도 ─────────────────
@patch("robust_client.time.sleep")
@patch("robust_client.requests.request")
def test_429_retry_after_respected(mock_req, mock_sleep):
    mock_req.side_effect = [
        _make_response(429, headers={"Retry-After": "2"}),
        _make_response(200, {"data": "success"}),
    ]

    result = call_api("http://example.com/api", max_retries=3)

    assert result == {"data": "success"}
    assert mock_req.call_count == 2
    # Retry-After=2 값으로 sleep 호출됐는지 확인
    mock_sleep.assert_called_once_with(2.0)
