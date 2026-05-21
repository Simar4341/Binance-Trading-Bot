# 🤖 Binance Futures Testnet — Trading Bot

A clean, structured Python CLI application for placing **MARKET**, **LIMIT**, and **STOP-LIMIT** orders on the Binance USDT-M Futures Testnet.

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # Binance REST client (signing, sessions, error handling)
│   ├── orders.py            # OrderManager — business logic + response formatting
│   ├── validators.py        # All input validation (collected errors, clear messages)
│   └── logging_config.py   # Rotating file + console logging setup
├── cli.py                   # Click CLI entry point
├── logs/
│   ├── market_order_sample.log
│   └── limit_order_sample.log
├── .env.example             # Credential template
├── .gitignore
├── requirements.txt
└── README.md
```

**Layer separation:**
- `client.py` — pure HTTP/API layer (no business logic)
- `orders.py` — order construction and response formatting
- `validators.py` — isolated, reusable validation
- `cli.py` — presentation layer only (no direct API calls)

---

## ⚙️ Setup

### 1. Get Testnet Credentials

1. Visit [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Go to **API Key** section → click **Generate Key**
4. Save your **API Key** and **Secret Key**

### 2. Clone & Install

```bash
git clone https://github.com/your-username/trading-bot.git
cd trading-bot

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure Credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> ⚠️ Never commit your `.env` file. It is listed in `.gitignore`.

---

## 🚀 How to Run

### Place a MARKET order

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side   BUY \
  --type   MARKET \
  --quantity 0.001
```

### Place a LIMIT order

```bash
python cli.py place-order \
  --symbol   ETHUSDT \
  --side     SELL \
  --type     LIMIT \
  --quantity 0.01 \
  --price    3200
```

### Place a STOP-LIMIT order *(bonus order type)*

```bash
python cli.py place-order \
  --symbol     BTCUSDT \
  --side       SELL \
  --type       STOP \
  --quantity   0.001 \
  --price      29000 \
  --stop-price 29500
```

### Interactive guided mode *(bonus UX)*

Prompts for each field with inline validation and a confirmation step before submitting:

```bash
python cli.py interactive
```

### View account balance & open positions

```bash
python cli.py account
```

### List open orders

```bash
python cli.py open-orders              # all symbols
python cli.py open-orders --symbol BTCUSDT
```

### Global options

| Flag | Default | Description |
|------|---------|-------------|
| `--log-dir PATH` | `logs/` | Directory for log files |
| `--base-url URL` | `https://testnet.binancefuture.com` | Override API base URL |

---

## 📤 Sample Output

### MARKET order

```
  ┌─ ORDER REQUEST SUMMARY ────────────────────────────────
  │  Symbol     : BTCUSDT
  │  Side       : BUY
  │  Type       : MARKET
  │  Quantity   : 0.001
  └──────────────────────────────────────────────────────

  ✅  ORDER PLACED SUCCESSFULLY
  ════════════════════════════════════════════════════
    ORDER DETAILS
  ════════════════════════════════════════════════════
    Order ID      : 4083469812
    Symbol        : BTCUSDT
    Side          : BUY
    Type          : MARKET
    Status        : FILLED
    Orig Qty      : 0.001
    Executed Qty  : 0.001
    Avg Price     : 42587.30
    Limit Price   : 0
    Time in Force : GTC
  ════════════════════════════════════════════════════
```

### Validation error (missing price on LIMIT order)

```
  ❌  Validation Error: Validation failed:
    • '--price' is required for LIMIT orders.
```

---

## 📋 Commands Reference

| Command | Description |
|---------|-------------|
| `place-order` | Place MARKET / LIMIT / STOP order via flags |
| `interactive` | Guided prompts with confirmation |
| `account` | Show USDT balance and open positions |
| `open-orders` | List open orders |

### `place-order` flags

| Flag | Required | Description |
|------|----------|-------------|
| `--symbol` / `-s` | ✅ | Trading pair e.g. `BTCUSDT` |
| `--side` / `-d` | ✅ | `BUY` or `SELL` |
| `--type` / `-t` | ✅ | `MARKET`, `LIMIT`, or `STOP` |
| `--quantity` / `-q` | ✅ | Asset quantity |
| `--price` / `-p` | LIMIT/STOP | Limit price |
| `--stop-price` / `-sp` | STOP | Trigger price |
| `--tif` | No | `GTC` (default) · `IOC` · `FOK` |

---

## 🪵 Logging

A new timestamped log file is created on every run:

```
logs/trading_bot_YYYYMMDD_HHMMSS.log
```

| What is logged | Level |
|----------------|-------|
| Every API request (params, URL) | `DEBUG` |
| Every API response (status, body excerpt) | `DEBUG` |
| Validation pass/fail details | `DEBUG` / `INFO` |
| Order accepted / rejected | `INFO` / `ERROR` |
| Network failures | `ERROR` |
| API keys / signatures | **Redacted** (`***redacted***`) |

Console shows `WARNING` and above only — keeping stdout clean for script use.
Full `DEBUG` trace is always in the log file.

Sample log files are included at:
- `logs/market_order_sample.log`
- `logs/limit_order_sample.log`

---

## 🔒 Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Missing `--price` on LIMIT/STOP | Validation error, exit code 2 |
| Non-numeric quantity or price | Validation error, exit code 2 |
| Binance rejects order (e.g. insufficient balance) | `BinanceAPIError` with Binance error code + message |
| Network timeout / unreachable host | `NetworkError` with clear message |
| Missing API credentials in `.env` | Exits immediately with setup instructions |

All errors are logged to file **and** printed to stderr with a clear ❌ indicator.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `click` | CLI framework (commands, options, prompts) |
| `requests` | HTTP client with session/keep-alive |
| `python-dotenv` | Load `.env` credentials into environment |

No Binance SDK required — all API calls are direct REST with HMAC-SHA256 signing.

---

## 💡 Assumptions

1. **Testnet only** — the default base URL is `https://testnet.binancefuture.com`. Point `--base-url` at `https://fapi.binance.com` for production (use at your own risk).
2. **USDT-M Futures** — only USDⓈ-margined futures endpoints are used.
3. **Hedge mode not assumed** — orders use `positionSide=BOTH` (one-way mode default).
4. **Quantity precision** — the user is responsible for passing quantities that satisfy the symbol's `LOT_SIZE` filter. A future enhancement could auto-query `GET /fapi/v1/exchangeInfo` and round automatically.
5. **Python 3.9+** required (uses standard-library `typing` patterns compatible with 3.9).

---

## 🎁 Bonus Features Implemented

- ✅ **STOP-LIMIT order type** (third order type beyond MARKET and LIMIT)
- ✅ **Interactive mode** (`python cli.py interactive`) — guided prompts, inline validation, confirmation step
- ✅ **Account overview** command with USDT balance and open positions table
- ✅ **Open orders** listing command

---

*Built for the PrimeTrade.ai Python Developer application task.*
