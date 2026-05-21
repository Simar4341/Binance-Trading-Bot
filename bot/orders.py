"""
Order placement logic — sits between the CLI layer and the API client.

OrderManager wraps the BinanceFuturesClient and provides typed helper
methods for each order type, centralising parameter assembly, logging
of the request summary, and formatting of the response.
"""

import logging
from typing import Optional

from bot.client import BinanceFuturesClient, BinanceAPIError, NetworkError
from bot.validators import validate_order_params

logger = logging.getLogger(__name__)


class OrderManager:
    """
    High-level order interface.

    Parameters
    ----------
    client: An initialised BinanceFuturesClient instance.
    """

    def __init__(self, client: BinanceFuturesClient) -> None:
        self.client = client

    # ------------------------------------------------------------------
    # Core placement method
    # ------------------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Validate inputs, build the Binance params dict, and submit the order.

        Returns
        -------
        The raw JSON response dict from Binance.

        Raises
        ------
        ValueError      — on invalid user input (propagated from validators).
        BinanceAPIError — on API-level rejections.
        NetworkError    — on transport failures.
        """
        logger.info(
            "Order requested | symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
            symbol, side, order_type, quantity, price, stop_price,
        )

        # --- validate + normalise ---
        symbol, side, order_type, quantity, price, stop_price = validate_order_params(
            symbol, side, order_type, quantity, price, stop_price
        )

        # --- build Binance params ---
        params: dict = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force

        elif order_type == "STOP":
            params["price"] = price          # limit price to fill at
            params["stopPrice"] = stop_price  # trigger price
            params["timeInForce"] = time_in_force

        logger.info("Submitting order params: %s", params)

        try:
            response = self.client.place_order(**params)
        except BinanceAPIError:
            logger.error("Order rejected by Binance API")
            raise
        except NetworkError:
            logger.error("Order could not be sent (network failure)")
            raise

        logger.info(
            "Order accepted | orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )
        return response

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def place_market_order(self, symbol: str, side: str, quantity: str) -> dict:
        """Place a MARKET order — executes immediately at best available price."""
        logger.info("Helper: market order | %s %s qty=%s", side, symbol, quantity)
        return self.place_order(symbol, side, "MARKET", quantity)

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        time_in_force: str = "GTC",
    ) -> dict:
        """Place a LIMIT order — rests in the book until price is reached."""
        logger.info(
            "Helper: limit order | %s %s qty=%s price=%s tif=%s",
            side, symbol, quantity, price, time_in_force,
        )
        return self.place_order(symbol, side, "LIMIT", quantity, price=price, time_in_force=time_in_force)

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: str,
        stop_price: str,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place a STOP-LIMIT order.
        Triggered when market reaches *stop_price*, then places a limit order at *price*.
        """
        logger.info(
            "Helper: stop-limit order | %s %s qty=%s price=%s stop=%s tif=%s",
            side, symbol, quantity, price, stop_price, time_in_force,
        )
        return self.place_order(
            symbol, side, "STOP", quantity,
            price=price, stop_price=stop_price, time_in_force=time_in_force,
        )

    # ------------------------------------------------------------------
    # Response formatter (used by CLI layer)
    # ------------------------------------------------------------------

    @staticmethod
    def format_response(response: dict) -> str:
        """Return a human-readable order response summary."""
        lines = [
            "━" * 52,
            "  ORDER DETAILS",
            "━" * 52,
            f"  Order ID      : {response.get('orderId', 'N/A')}",
            f"  Symbol        : {response.get('symbol', 'N/A')}",
            f"  Side          : {response.get('side', 'N/A')}",
            f"  Type          : {response.get('type', 'N/A')}",
            f"  Status        : {response.get('status', 'N/A')}",
            f"  Orig Qty      : {response.get('origQty', 'N/A')}",
            f"  Executed Qty  : {response.get('executedQty', 'N/A')}",
            f"  Avg Price     : {response.get('avgPrice', 'N/A')}",
            f"  Limit Price   : {response.get('price', 'N/A')}",
        ]
        stop = response.get("stopPrice")
        if stop and stop != "0":
            lines.append(f"  Stop Price    : {stop}")
        lines += [
            f"  Time in Force : {response.get('timeInForce', 'N/A')}",
            f"  Client OrdId  : {response.get('clientOrderId', 'N/A')}",
            f"  Update Time   : {response.get('updateTime', 'N/A')}",
            "━" * 52,
        ]
        return "\n".join(lines)
