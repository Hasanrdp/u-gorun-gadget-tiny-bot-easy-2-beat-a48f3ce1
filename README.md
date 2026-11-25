[![make.fun](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![rank](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/Hasanrdp/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/rank.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![reward](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/Hasanrdp/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/reward.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

# Capitulation Bounce Bot

A tiny paper-trading bot for the "Tiny Bot, Easy $2: Beat Buy-and-Hold on
Solana" bounty. It trades the hourly bars of FARTCOIN, JITOSOL, POPCAT, RAY,
SOL, WETH and WIF, holds only long positions, and never touches the network —
every decision comes from the bars the harness sends it.

## How it works

Solana coins mean-revert hard at the daily and six-hour scale: on the kit's
dev window the lag-1 correlation of six-hour returns is about -0.38 and of
daily returns about -0.79. A sharp fall is usually followed by a bounce, so
the bot buys the fall and sells the bounce — fast, before the drift resumes.

**Entry** (decided on a bar's close, filled at the next bar's open):

- the close sits at least **4% below the highest close of the last 24 bars**,
  and
- **RSI(14) is at or below 35** — the fall is genuinely oversold, not just
  drifting down.

One position per symbol; each buy spends **22% of equity**, just under the
25% per-symbol weight cap, limited by the cash the reply still holds.

**Exit** (checked every bar, whole position, sells sent before buys):

- take profit at **+3.0%** over cost,
- stop loss at **-1.5%** under cost,
- time stop: out after **8 bars** held, whatever the price.

After a sell the symbol rests **3 bars** before it may be bought again. No
shorts, no leverage, no pyramiding, no chasing: a symbol that never dips 4%
with an RSI at or under 35 is never bought.

## Local result (kit dev window, 136 hourly bars)

Graded with the kit's own grader (`grade-local --driver process`):

| Metric | Value |
| --- | --- |
| Net PnL | **+$630.87** on $10,000 |
| Return | +6.31% |
| Trades | 42 (min. 8 required) |
| Max drawdown | 1.8% (max. 25% allowed) |
| Fees paid | $92.19 |

For comparison, on the same window the house baselines score: buy-and-hold
-$869.34, EMA-cross -$173.04, momentum -$268.23, RSI-Bollinger -$56.49,
MACD-CCI -$20.22, ADX-momentum -$114.42, hold-cash $0.00. The dev window
splits into a crash-and-bounce first half (+$589.89) and a slow grind second
half (+$40.94); the bot stays positive in both.

## Files

- `main.py` — the entrypoint; pure-stdlib Python 3, runs on the kit's shim.
- `vendor/makefun_bars.py` — the kit's `sdk/makefun_bars.py`, copied
  byte-identical; it speaks the `agent-fun/bars-replay/v1` line protocol.
- `.makefun/owner.json` — the payout wallet that claims any prize.

## Reproduce

From the unpacked kit directory:

```sh
node cli/makefun.mjs grade-local --kit . --bot <this repository> --driver process
```

The bot is fully deterministic: no clock, no environment, no randomness. It
runs twice on the grader and the two action logs match byte for byte.
