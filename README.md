# Northstar BTC

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/adheyusuf230801-ship-it/btc-race-24h-20261117-0603-codex/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/adheyusuf230801-ship-it/btc-race-24h-20261117-0603-codex/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

A defensive, long-only CBBTC paper trading bot for make.fun's “Race a BTC trading bot live for 24 hours.” Python 3.13 standard library only, with the unchanged vendored protocol shim. Run with `python3 -P -s main.py`; feed agent-fun/bars-replay/v1 JSON lines on stdin. Stdout contains only replies, one per batch with its sequence echoed.

The bot waits for 240 observed bars. A 60-bar EMA must exceed a rising 240-bar EMA by 20 basis points, price must exceed the slow EMA, and the 120-bar return must exceed 20 basis points. That regime must persist for five observed bars. Entry then requires a pullback to within 10 basis points above the fast EMA and a positive five-bar return. This buys a recovery within a broader trend rather than chasing a spike.

One entry uses at most 100% of equity, bounded further by available cash and the harness weight and position caps. Estimated impact above 10 basis points blocks entry. Orders allow at most 50 basis points of total slippage; minimum notional is respected. Positions are never topped up. Exits sell the whole holding on any of:

- Five bars with the fast EMA more than 50 basis points below the slow EMA and price below the slow EMA.
- A 75-basis-point decline from the highest observed close while held.
- Price 60 basis points above the fee-inclusive entry cost basis, banking a modest trend gain.
- A 2% equity drawdown from the account peak, which permanently disables further entries for that run.

A completed exit starts a 180-batch cooldown. Failed exits remain latched for retry. Each reply contains at most one order; sell proceeds are only available on a later batch. Warm-up builds indicators without trading. Missing CBBTC bars do not advance indicators. Stops are decisions at closes, filled at the next open, so gaps and rejected orders can exceed the intended risk limit.

All decisions use only supplied bars and account state, with integer arithmetic and bounded price history. There is no clock, environment lookup, network, randomness, or runtime data-file access. Parameters express general trend, cost, and risk rules; no prices, dates, or bar-specific actions are embedded.

Frozen dev window references (1,440 one-minute CBBTC bars, kit grade-local with `--driver process`):

| Bot | Net PnL (USDC) | Trades |
| --- | ---: | ---: |
| Buy-and-hold | +1.07 | 1 |
| Momentum baseline | +2.45 | 1 |
| EMA-cross | -106.21 | 68 |
| ADX-momentum | -32.66 | 26 |
| RSI-Bollinger | -24.25 | 11 |
| Hold cash | 0.00 | 0 |

The dev window has only about +0.1% drift, so transaction costs matter. A throwaway offline simulator in `/tmp` replayed all dev bars through `BarsState` and `on_batch`, using next-open fills, 4 bps fees, 2 bps slippage and constant-product depth impact, including final liquidation. The new replay returned **+4.502729 USDC**, with **2 trades (one round trip)**, **0.79 USDC fees**, **0.55% maximum drawdown**, and **1,004.502729 USDC final equity** from 1,000 USDC. Two runs produced byte-identical order logs. The sizing sweep found one rare confirmed-trend signal per window, with PnL scaling with size and dev drawdown below 0.6%; entry and exit parameters remain unchanged to avoid chasing this window. These limited checks are not proof of out-of-sample profitability. The simulator approximates execution and does not replace the official grade.

`python3 -m py_compile main.py` and a direct hello/three-batch/done protocol smoke test were run locally. Official grade-local, kit checks, transcript packaging and submission are left to the orchestrator; screenshots are not applicable. Nothing has been submitted by this bot-building session.

MIT licensed; see LICENSE.
