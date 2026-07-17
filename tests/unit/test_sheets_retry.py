"""Unit tests for GoogleSheetsSubmitter._retry_on_transient.

Validates:
  - Successful call is invoked exactly once
  - 429 / 500 / 502 / 503 / 504 APIError triggers retries
  - Non-retryable APIError (e.g. 403) is re-raised immediately
  - ConnectionError / TimeoutError / OSError are retried
  - After max_retries exhausted the last exception is re-raised
  - Success on second attempt (first fails, second succeeds)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------
from modules.google_sheets.submitter import GoogleSheetsSubmitter

_retry = GoogleSheetsSubmitter._retry_on_transient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api_error(status_code: int):
    """Return a gspread.exceptions.APIError mock with the given HTTP status."""
    import gspread.exceptions  # noqa: PLC0415

    response_mock = MagicMock()
    response_mock.status_code = status_code
    err = gspread.exceptions.APIError(response_mock)
    err.response = response_mock
    return err


# ---------------------------------------------------------------------------
# Tests – happy path
# ---------------------------------------------------------------------------

class TestRetryHappyPath:

    def test_success_calls_fn_once(self):
        fn = MagicMock()
        with patch("time.sleep"):
            _retry(fn, max_retries=3)
        fn.assert_called_once()

    def test_success_on_second_attempt(self):
        attempts = []

        def fn():
            attempts.append(1)
            if len(attempts) == 1:
                raise _make_api_error(429)

        with patch("time.sleep"):
            _retry(fn, max_retries=3)

        assert len(attempts) == 2


# ---------------------------------------------------------------------------
# Tests – retryable HTTP status codes
# ---------------------------------------------------------------------------

class TestRetryableStatusCodes:

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_retryable_status_retries_and_raises_after_max(self, status):
        fn = MagicMock(side_effect=_make_api_error(status))
        with patch("time.sleep"), pytest.raises(type(_make_api_error(status))):
            _retry(fn, max_retries=3)
        assert fn.call_count == 3

    @pytest.mark.parametrize("status", [429, 500, 503])
    def test_retryable_uses_exponential_backoff(self, status):
        fn = MagicMock(side_effect=_make_api_error(status))
        sleep_mock = MagicMock()
        with patch("time.sleep", sleep_mock), pytest.raises(type(_make_api_error(status))):
            _retry(fn, max_retries=3)
        # Exponential backoff: 2^0=1s, 2^1=2s, 2^2=4s (last attempt doesn't sleep)
        sleep_calls = [c.args[0] for c in sleep_mock.call_args_list]
        assert sleep_calls == [1, 2, 4]


# ---------------------------------------------------------------------------
# Tests – non-retryable HTTP status code
# ---------------------------------------------------------------------------

class TestNonRetryableStatusCode:

    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_non_retryable_raises_immediately(self, status):
        fn = MagicMock(side_effect=_make_api_error(status))
        with patch("time.sleep"), pytest.raises(type(_make_api_error(status))):
            _retry(fn, max_retries=3)
        fn.assert_called_once()  # no retry, raised immediately


# ---------------------------------------------------------------------------
# Tests – network errors
# ---------------------------------------------------------------------------

class TestNetworkErrors:

    @pytest.mark.parametrize("exc_cls", [ConnectionError, TimeoutError, OSError])
    def test_network_error_retried(self, exc_cls):
        fn = MagicMock(side_effect=exc_cls("network failure"))
        with patch("time.sleep"), pytest.raises(exc_cls):
            _retry(fn, max_retries=3)
        assert fn.call_count == 3

    def test_network_error_success_on_retry(self):
        call_count = [0]

        def fn():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("transient")

        with patch("time.sleep"):
            _retry(fn, max_retries=3)

        assert call_count[0] == 3


# ---------------------------------------------------------------------------
# Tests – max_retries boundary
# ---------------------------------------------------------------------------

class TestMaxRetriesBoundary:

    def test_max_retries_1_does_not_retry(self):
        fn = MagicMock(side_effect=_make_api_error(429))
        with patch("time.sleep"), pytest.raises(type(_make_api_error(429))):
            _retry(fn, max_retries=1)
        fn.assert_called_once()

    def test_max_retries_0_raises_immediately(self):
        fn = MagicMock()
        with patch("time.sleep"), pytest.raises(RuntimeError, match="no attempts"):
            _retry(fn, max_retries=0)
        fn.assert_not_called()
