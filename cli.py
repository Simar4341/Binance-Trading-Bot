#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Testnet Trading Bot.

Usage examples
--------------
# Market order
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit order
python cli.py place-order --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500

# Stop-limit order
python cli.py place-order --symbol BTCUSDT --side SELL --type STOP --quantity 0.001 --price 29000 --stop-price 29500

# Interactive guided mode
python cli.py interactive

# Account balances
python cli.py account
"""

import os
import sys
import logging

import click
from dotenv import load_dotenv

from bot.logging_config import setup_logging
from bot.client import BinanceFuturesClient, BinanceAPIError, NetworkError
from bot.orders import OrderManager

load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(base_url: str) -> BinanceFuturesClient:
    """Build a client from env vars, exiting with a clear message if absent."""
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        click.echo(
            "\n❌  Missing credentials.\n"
            "    Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file "
            "or as environment variables.\n",
            err=True,
        )
        sys.exit(1)
    return BinanceFuturesClient(api_key, api_secret, base_url)


def _echo_request_summary(symbol, side, order_type, quantity, price, stop_price, tif):
    """Print a clean order-request summary block."""
    click.echo()
    click.echo(click.style("  ┌─ ORDER REQUEST SUMMARY ", fg="cyan") + "─" * 28)
    click.echo(f"  │  Symbol     : {symbol.upper()}")
    click.echo(f"  │  Side       : {side.upper()}")
    click.echo(f"  │  Type       : {order_type.upper()}")
    click.echo(f"  │  Quantity   : {quantity}")
    if price:
        click.echo(f"  │  Price      : {price}")
    if stop_price:
        click.echo(f"  │  Stop Price : {stop_price}")
    if order_type.upper() != "MARKET":
        click.echo(f"  │  TIF        : {tif}")
    click.echo("  └" + "─" * 50)


def _echo_success(response: dict) -> None:
    click.echo()
    click.echo(click.style("  ✅  ORDER PLACED SUCCESSFULLY", fg="green", bold=True))
    click.echo(OrderManager.format_response(response))


def _echo_error(label: str, exc: Exception) -> None:
    click.echo()
    click.echo(click.style(f"  ❌  {label}: {exc}", fg="red", bold=True), err=True)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--log-dir",
    default="logs",
    show_default=True,
    help="Directory for log files.",
    envvar="BOT_LOG_DIR",
)
@click.option("--base-url", default="https://testnet.binancefuture.com", show_default=True,
              help="Binance Futures base URL.", envvar="BINANCE_BASE_URL")
@click.pass_context
def cli(ctx: click.Context, log_dir: str, base_url: str) -> None:
    """
    \b
    ╔══════════════════════════════════════════════╗
    ║   Binance Futures Testnet  —  Trading Bot    ║
    ╚══════════════════════════════════════════════╝
    Place MARKET, LIMIT, and STOP-LIMIT orders on the
    Binance USDT-M Futures testnet from the command line.
    """
    ctx.ensure_object(dict)
    log_file = setup_logging(log_dir)
    ctx.obj["log_file"] = log_file
    ctx.obj["base_url"] = base_url
    logger.info("CLI started | base_url=%s log_file=%s", base_url, log_file)


# ---------------------------------------------------------------------------
# place-order command
# ---------------------------------------------------------------------------


@cli.command("place-order")
@click.option("--symbol",     "-s", required=True,  help="Trading pair (e.g. BTCUSDT).")
@click.option("--side",       "-d", required=True,
              type=click.Choice(["BUY", "SELL"], case_sensitive=False),
              help="Order direction.")
@click.option("--type",  "order_type", "-t", required=True,
              type=click.Choice(["MARKET", "LIMIT", "STOP"], case_sensitive=False),
              help="Order type.")
@click.option("--quantity",   "-q", required=True,  help="Asset quantity (e.g. 0.001).")
@click.option("--price",      "-p", default=None,   help="Limit price (required for LIMIT / STOP).")
@click.option("--stop-price", "-sp", default=None,  help="Stop trigger price (required for STOP).")
@click.option("--tif",        default="GTC",
              type=click.Choice(["GTC", "IOC", "FOK"], case_sensitive=False),
              show_default=True, help="Time-in-force (LIMIT / STOP only).")
@click.pass_context
def place_order(
    ctx: click.Context,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str,
    stop_price: str,
    tif: str,
) -> None:
    """Place a single order (MARKET / LIMIT / STOP-LIMIT)."""

    _echo_request_summary(symbol, side, order_type, quantity, price, stop_price, tif)

    try:
        client = _make_client(ctx.obj["base_url"])
        manager = OrderManager(client)
        response = manager.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=tif.upper(),
        )
        _echo_success(response)

    except ValueError as exc:
        logger.warning("Validation error: %s", exc)
        _echo_error("Validation Error", exc)
        sys.exit(2)

    except BinanceAPIError as exc:
        logger.error("Binance API error: %s", exc)
        _echo_error("Binance API Error", exc)
        sys.exit(1)

    except NetworkError as exc:
        logger.error("Network error: %s", exc)
        _echo_error("Network Error", exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# interactive command  (BONUS: enhanced CLI UX)
# ---------------------------------------------------------------------------


@cli.command("interactive")
@click.pass_context
def interactive(ctx: click.Context) -> None:
    """
    \b
    Guided interactive order placement.
    Prompts for each field with inline validation and a confirmation step.
    """
    click.echo()
    click.echo(click.style("  🤖  Interactive Order Placement", fg="cyan", bold=True))
    click.echo("  " + "─" * 46)

    # --- collect inputs with inline validation ---
    while True:
        symbol = click.prompt("  Symbol (e.g. BTCUSDT)").strip().upper()
        if symbol.isalnum() and len(symbol) >= 3:
            break
        click.echo(click.style("  ⚠  Symbol must be alphanumeric and at least 3 chars.", fg="yellow"))

    side = click.prompt(
        "  Side",
        type=click.Choice(["BUY", "SELL"], case_sensitive=False),
    ).upper()

    order_type = click.prompt(
        "  Order type",
        type=click.Choice(["MARKET", "LIMIT", "STOP"], case_sensitive=False),
    ).upper()

    while True:
        quantity = click.prompt("  Quantity").strip()
        try:
            from decimal import Decimal
            if Decimal(quantity) > 0:
                break
        except Exception:
            pass
        click.echo(click.style("  ⚠  Quantity must be a positive number.", fg="yellow"))

    price = None
    stop_price = None

    if order_type in ("LIMIT", "STOP"):
        while True:
            price = click.prompt("  Limit price").strip()
            try:
                if Decimal(price) > 0:
                    break
            except Exception:
                pass
            click.echo(click.style("  ⚠  Price must be a positive number.", fg="yellow"))

    if order_type == "STOP":
        while True:
            stop_price = click.prompt("  Stop (trigger) price").strip()
            try:
                if Decimal(stop_price) > 0:
                    break
            except Exception:
                pass
            click.echo(click.style("  ⚠  Stop price must be a positive number.", fg="yellow"))

    tif = "GTC"
    if order_type != "MARKET":
        tif = click.prompt(
            "  Time-in-force",
            type=click.Choice(["GTC", "IOC", "FOK"], case_sensitive=False),
            default="GTC",
        ).upper()

    # --- confirmation ---
    click.echo()
    _echo_request_summary(symbol, side, order_type, quantity, price, stop_price, tif)
    click.echo()

    if not click.confirm(click.style("  Confirm and submit order?", fg="yellow")):
        click.echo(click.style("  ✗  Order cancelled.", fg="red"))
        logger.info("Interactive order cancelled by user.")
        return

    # --- submit ---
    try:
        client = _make_client(ctx.obj["base_url"])
        manager = OrderManager(client)
        response = manager.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=tif,
        )
        _echo_success(response)

    except ValueError as exc:
        logger.warning("Validation error (interactive): %s", exc)
        _echo_error("Validation Error", exc)
        sys.exit(2)

    except BinanceAPIError as exc:
        logger.error("API error (interactive): %s", exc)
        _echo_error("Binance API Error", exc)
        sys.exit(1)

    except NetworkError as exc:
        logger.error("Network error (interactive): %s", exc)
        _echo_error("Network Error", exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# account command
# ---------------------------------------------------------------------------


@cli.command("account")
@click.pass_context
def account(ctx: click.Context) -> None:
    """Display account balance and open positions."""
    try:
        client = _make_client(ctx.obj["base_url"])
        info = client.get_account()

        click.echo()
        click.echo(click.style("  💰  Account Overview", fg="cyan", bold=True))
        click.echo("  " + "─" * 46)

        # Assets
        usdt = next((a for a in info.get("assets", []) if a["asset"] == "USDT"), None)
        if usdt:
            click.echo(f"  Wallet Balance   : {float(usdt.get('walletBalance', 0)):>15.4f} USDT")
            click.echo(f"  Available Balance: {float(usdt.get('availableBalance', 0)):>15.4f} USDT")
            click.echo(f"  Unrealised PnL   : {float(usdt.get('unrealizedProfit', 0)):>15.4f} USDT")
        else:
            click.echo("  No USDT balance found.")

        # Open positions
        positions = [
            p for p in info.get("positions", [])
            if float(p.get("positionAmt", 0)) != 0
        ]
        click.echo()
        if positions:
            click.echo(click.style("  Open Positions", bold=True))
            click.echo(f"  {'Symbol':<12} {'Amount':>12} {'Entry Price':>14} {'Unreal. PnL':>14}")
            click.echo("  " + "─" * 54)
            for pos in positions:
                click.echo(
                    f"  {pos['symbol']:<12} "
                    f"{float(pos['positionAmt']):>12.6f} "
                    f"{float(pos['entryPrice']):>14.4f} "
                    f"{float(pos['unrealizedProfit']):>14.4f}"
                )
        else:
            click.echo("  No open positions.")

        click.echo("  " + "─" * 46)
        logger.info("Account info displayed successfully.")

    except BinanceAPIError as exc:
        logger.error("API error fetching account: %s", exc)
        _echo_error("Binance API Error", exc)
        sys.exit(1)

    except NetworkError as exc:
        logger.error("Network error fetching account: %s", exc)
        _echo_error("Network Error", exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# open-orders command
# ---------------------------------------------------------------------------

@cli.command("open-orders")
@click.option("--symbol", "-s", default=None, help="Filter by symbol (optional).")
@click.pass_context
def open_orders(ctx: click.Context, symbol: str) -> None:
    """List all open orders (optionally filtered by symbol)."""
    try:
        client = _make_client(ctx.obj["base_url"])
        orders = client.get_open_orders(symbol)

        click.echo()
        click.echo(click.style("  📋  Open Orders", fg="cyan", bold=True))
        click.echo("  " + "─" * 70)

        if not orders:
            click.echo("  No open orders.")
        else:
            click.echo(
                f"  {'OrderId':>12} {'Symbol':<10} {'Side':<6} {'Type':<12} "
                f"{'Qty':>10} {'Price':>10} {'Status':<10}"
            )
            click.echo("  " + "─" * 70)
            for o in orders:
                click.echo(
                    f"  {o['orderId']:>12} {o['symbol']:<10} {o['side']:<6} "
                    f"{o['type']:<12} {o['origQty']:>10} {o['price']:>10} {o['status']:<10}"
                )

        click.echo("  " + "─" * 70)
        logger.info("Open orders listed | count=%d", len(orders) if isinstance(orders, list) else 0)

    except BinanceAPIError as exc:
        _echo_error("Binance API Error", exc)
        sys.exit(1)
    except NetworkError as exc:
        _echo_error("Network Error", exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli(obj={})
