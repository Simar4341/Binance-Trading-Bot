"""
Low-level Binance Futures REST client.

Responsibilities
----------------
* HMAC-SHA256 request signing
* Session management and keep-alive
* Uniform error translation into BinanceAPIError / NetworkError
* DEBUG-level logging of every request and response (secrets redacted)
"""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
REQUEST_TIMEOUT = 10  # seconds


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response or an error payload."""

    def __init__(self, message: str, code: Optional[int] = None):
        self.code = code
        super().__init__(f"[{code}] {message}" if code else message)


class NetworkError(Exception):
    """Raised for connection failures, timeouts, or other transport issues."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures REST API.

    Parameters
    ----------
    api_key:    Binance API key (from testnet dashboard).
    api_secret: Binance API secret.
    base_url:   Override to point at a different environment.
    timeout:    Per-request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self.api_key = api_key
        self._api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})
        logger.info("BinanceFuturesClient ready | base_url=%s", self.base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add timestamp + HMAC-SHA256 signature to *params* (mutates in place)."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        sig = hmac.new(self._api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of *params* with the signature masked."""
        safe = dict(params)
        if "signature" in safe:
            safe["signature"] = "***redacted***"
        return safe

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Any:
        """
        Execute an HTTP request and return the parsed JSON response.

        Raises
        ------
        BinanceAPIError  on API-level errors (4xx / 5xx with JSON body).
        NetworkError     on transport-level failures.
        """
        url = f"{self.base_url}{endpoint}"
        params = dict(params) if params else {}

        if signed:
            params = self._sign(params)

        logger.debug(
            "→ %s %s | params=%s", method.upper(), url, self._redact(params)
        )

        try:
            if method.upper() == "GET":
                resp = self._session.get(url, params=params, timeout=self.timeout)
            else:  # POST / DELETE / PUT
                resp = self._session.request(
                    method, url, data=params, timeout=self.timeout
                )

            logger.debug(
                "← %s %s | status=%d | body=%s",
                method.upper(),
                endpoint,
                resp.status_code,
                resp.text[:500],  # cap to avoid huge log lines
            )

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.HTTPError as exc:
            body: Dict = {}
            try:
                body = exc.response.json()
            except Exception:
                pass
            code = body.get("code")
            msg = body.get("msg", str(exc))
            logger.error("API error | code=%s msg=%s", code, msg)
            raise BinanceAPIError(msg, code) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error | %s", exc)
            raise NetworkError(f"Could not reach {self.base_url}: {exc}") from exc

        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out | endpoint=%s", endpoint)
            raise NetworkError(f"Request timed out ({self.timeout}s): {exc}") from exc

        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error | %s", exc)
            raise NetworkError(f"Request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the API server is reachable."""
        try:
            self._request("GET", "/fapi/v1/ping")
            logger.info("Ping successful")
            return True
        except (BinanceAPIError, NetworkError):
            return False

    def get_server_time(self) -> int:
        """Return server timestamp in milliseconds."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self) -> Dict:
        """Return exchange trading rules and symbol info (public endpoint)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> Dict:
        """Return account asset balances and open positions (signed)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, **kwargs: Any) -> Dict:
        """
        Place a new order.  All keyword arguments are forwarded directly to
        POST /fapi/v1/order after adding a timestamp and signature.

        Common kwargs
        -------------
        symbol, side, type, quantity, price, stopPrice, timeInForce, reduceOnly
        """
        return self._request("POST", "/fapi/v1/order", params=kwargs, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an existing open order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
