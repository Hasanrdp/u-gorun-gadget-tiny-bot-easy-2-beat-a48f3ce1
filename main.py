"""Capitulation Bounce Bot — a tiny dip-buying bot for the solana-bars-1h replay.

Idea, in one line: Solana memecoins and majors mean-revert hard at the daily
and six-hour scale (on the kit's dev window the lag-1 correlation of six-hour
returns is about -0.38 and of daily returns about -0.79), so the bot buys a
symbol only after it has fallen a long way from its recent high while its RSI
says it is oversold, then sells the bounce fast — never holding a loser.

Entry (decided on a bar's close, filled at the next bar's open):
  * the close sits at least 4% below the highest close of the last 24 bars, and
  * RSI(14) is at or below 35.
  * one position per symbol; each buy spends 22% of equity (just under the
    25% per-symbol weight cap), limited by the cash left in the reply.

Exit (checked every bar, whole position, sells first):
  * take profit at +3.0% over cost, stop loss at -1.5% under cost, or
  * a time stop: out after 8 bars held, whatever the price.
  * after a sell, the symbol rests 3 bars before it may be bought again.

Everything is deterministic: no clock, no environment, no randomness — only
the closes the harness sends, integer arithmetic for money, and float64 for
the two ratios. The bot runs on the kit's Python shim (vendor/makefun_bars.py),
standard library only.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

BPS = 10000
SYMBOLS = ["FARTCOIN", "JITOSOL", "POPCAT", "RAY", "SOL", "WETH", "WIF"]

# Entry: how far the close must sit below its 24-bar high, and how oversold.
DIP_BARS = 24
DIP_PCT = 0.04
RSI_BARS = 14
RSI_MAX = 35.0
# Sizing: share of equity per buy (the harness caps a symbol at 25%).
STAKE_FRAC = 0.22
# Exits: take profit / stop loss in basis points over cost, max hold in bars.
TAKE_BPS = 300
STOP_BPS = 150
HOLD_BARS = 8
# Rest after a sell, in bars, before the symbol may be bought again.
COOLDOWN_BARS = 3
# Cap on the adverse move from the decision close the bot accepts at a fill.
MAX_SLIPPAGE_BPS = 100


def rsi(closes, period):
    """RSI over the close list: mean gain over mean loss across the window.

    Returns None until period + 1 closes have been seen. A window with no
    losing bar reads 100, one with no gaining bar reads 0.
    """
    if len(closes) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(len(closes) - period, len(closes)):
        move = closes[i] - closes[i - 1]
        if move > 0:
            gains += move
        else:
            losses -= move
    if losses == 0:
        return 100.0
    if gains == 0:
        return 0.0
    return 100.0 - 100.0 / (1.0 + (gains / period) / (losses / period))


# Per-symbol close history (ints, oldest first) and bookkeeping.
closes = {symbol: [] for symbol in SYMBOLS}
entry_bar = {}   # symbol -> batch seq where its position first appeared
last_sell = {}   # symbol -> batch seq where its sell was decided


def on_batch(state, batch):
    for bar in batch["bars"]:
        symbol = bar["symbol"]
        if symbol in closes:
            closes[symbol].append(int(bar["c"]))
    if state.warming_up:
        return []
    orders = []
    cash = state.cash
    equity = state.equity

    # A position that is gone (sold, or flattened) forgets its entry bar; a
    # sell the market refused keeps the original one, so its age keeps
    # growing and the time stop fires again on the next bar.
    for symbol in list(entry_bar):
        if symbol not in state.positions:
            del entry_bar[symbol]

    # Exits first: sells never fund this reply's buys, so they go first.
    for symbol, held in list(state.positions.items()):
        if symbol not in entry_bar:
            entry_bar[symbol] = state.seq
        value = state.value(symbol, held.qty)
        age = state.seq - entry_bar[symbol]
        if (value * BPS >= held.cost * (BPS + TAKE_BPS)
                or value * BPS <= held.cost * (BPS - STOP_BPS)
                or age >= HOLD_BARS):
            orders.append({"side": "sell", "symbol": symbol, "qty": held.qty,
                           "max_slippage_bps": MAX_SLIPPAGE_BPS})
            last_sell[symbol] = state.seq

    # Entries: dip plus oversold, one fresh position per symbol.
    for symbol in SYMBOLS:
        if symbol in state.positions:
            continue
        history = closes[symbol]
        if len(history) < max(DIP_BARS, RSI_BARS) + 1:
            continue
        if state.seq - last_sell.get(symbol, -10 ** 9) < COOLDOWN_BARS:
            continue
        high = max(history[-DIP_BARS:])
        dip = history[-1] / high - 1.0
        if dip > -DIP_PCT:
            continue
        strength = rsi(history, RSI_BARS)
        if strength is None or strength > RSI_MAX:
            continue
        stake = int(equity * STAKE_FRAC)
        room = state.weight_room(symbol)
        if stake > room:
            stake = room
        if stake > cash:
            stake = cash
        if stake < 1_000_000:
            continue
        orders.append({"side": "buy", "symbol": symbol,
                       "notional_quote_units": stake,
                       "max_slippage_bps": MAX_SLIPPAGE_BPS})
        cash -= stake
    return orders


makefun_bars.run(on_batch)
