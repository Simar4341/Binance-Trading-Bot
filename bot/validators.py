"""
Input validation for trading-bot order parameters.

All public functions either return the cleaned/normalised value
or raise ``ValueError`` with a human-readable message.
``validate_order_params`` is the single entry-point used by OrderManager.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

VALID_SIDES: frozenset = frozenset({"BUY", "SELL"})
VALID_ORDER_TYPES: frozenset = frozenset({"MARKET", "LIMIT", "STOP"})
VALID_TIF: frozenset = frozenset({"GTC", "IOC", "FOK"})


# ------------------------------------------------------------------
# Individual field validators
# ------------------------------------------------------------------


def validate_symbol(symbol: str) -> str:
    """Normalise and validate a trading pair symbol."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol must not be empty.")
    if not symbol.isalnum():
        raise ValueError(
            f"Invalid symbol '{symbol}': must contain only letters and digits (e.g. BTCUSDT)."
        )
    if len(symbol) < 3:
        raise ValueError(f"Invalid symbol '{symbol}': too short (minimum 3 characters).")
    logger.debug("Symbol validated: %s", symbol)
    return symbol


def validate_side(side: str) -> str:
    """Normalise and validate order side."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}': must be one of {sorted(VALID_SIDES)}."
        )
    logger.debug("Side validated: %s", side)
    return side


def validate_order_type(order_type: str) -> str:
    """Normalise and validate order type."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}': must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    logger.debug("Order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity: str) -> str:
    """Validate that quantity is a positive decimal number."""
    try:
        qty = Decimal(str(quantity).strip())
    except InvalidOperation:
        raise ValueError(
            f"Invalid quantity '{quantity}': must be a numeric value (e.g. 0.001)."
        )
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0, got {qty}.")
    logger.debug("Quantity validated: %s", qty)
    return str(qty)


def validate_price(value: str, field_name: str = "price") -> str:
    """Validate that *value* is a positive decimal number suitable for a price field."""
    try:
        price = Decimal(str(value).strip())
    except InvalidOperation:
        raise ValueError(
            f"Invalid {field_name} '{value}': must be a numeric value (e.g. 30000.50)."
        )
    if price <= 0:
        raise ValueError(f"{field_name.capitalize()} must be greater than 0, got {price}.")
    logger.debug("%s validated: %s", field_name.capitalize(), price)
    return str(price)


def validate_tif(tif: str) -> str:
    """Validate time-in-force string."""
    tif = tif.strip().upper()
    if tif not in VALID_TIF:
        raise ValueError(
            f"Invalid time-in-force '{tif}': must be one of {sorted(VALID_TIF)}."
        )
    return tif


# ------------------------------------------------------------------
# Composite validator
# ------------------------------------------------------------------


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> Tuple[str, str, str, str, Optional[str], Optional[str]]:
    """
    Validate and normalise all order parameters at once.

    Returns
    -------
    Tuple of (symbol, side, order_type, quantity, price, stop_price)
    with all values cleaned / normalised.

    Raises
    ------
    ValueError — if any validation rule is violated.
                 All errors are collected and reported together.
    """
    errors: List[str] = []

    # --- individual field validation (collect all errors) ---
    clean_symbol = clean_side = clean_type = clean_qty = clean_price = clean_stop = None

    for fn, val, label in [
        (validate_symbol, symbol, "symbol"),
        (validate_side, side, "side"),
        (validate_order_type, order_type, "order_type"),
        (validate_quantity, quantity, "quantity"),
    ]:
        try:
            result = fn(val)
            if label == "symbol":
                clean_symbol = result
            elif label == "side":
                clean_side = result
            elif label == "order_type":
                clean_type = result
            elif label == "quantity":
                clean_qty = result
        except ValueError as exc:
            errors.append(str(exc))

    # --- cross-field validation (only meaningful once base fields are clean) ---
    resolved_type = clean_type or order_type.strip().upper()

    if resolved_type in ("LIMIT", "STOP"):
        if price is None or str(price).strip() == "":
            errors.append(f"'--price' is required for {resolved_type} orders.")
        else:
            try:
                clean_price = validate_price(price, "price")
            except ValueError as exc:
                errors.append(str(exc))

    if resolved_type == "STOP":
        if stop_price is None or str(stop_price).strip() == "":
            errors.append("'--stop-price' is required for STOP orders.")
        else:
            try:
                clean_stop = validate_price(stop_price, "stop_price")
            except ValueError as exc:
                errors.append(str(exc))

    if errors:
        bullet_list = "\n".join(f"  • {e}" for e in errors)
        raise ValueError(f"Validation failed:\n{bullet_list}")

    logger.info(
        "Order params validated | symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
        clean_symbol, clean_side, clean_type, clean_qty, clean_price, clean_stop,
    )
    return clean_symbol, clean_side, clean_type, clean_qty, clean_price, clean_stop
