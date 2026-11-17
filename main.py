"""Northstar BTC: patient, risk-capped trend following; no external inputs."""
from collections import deque
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))
import makefun_bars

SYMBOL = 'CBBTC'
FAST = 60
SLOW = 240
MOMENTUM = 120
CONFIRM = 5
COOLDOWN = 180
# One rare confirmed-trend signal/window: PnL scales linearly with size; dev
# drawdown stays under 0.6%. The 2% halt and trailing stop bound downside.
WEIGHT_BPS = 10000
TRAIL_BPS = 75
DRAWDOWN_BPS = 200
MAX_SLIPPAGE_BPS = 50
TAKE_PROFIT_BPS = 60


class Northstar:
    def __init__(self):
        self.closes = deque(maxlen=MOMENTUM + 1)
        self.fast = self.slow = None
        self.count = self.confirm = self.breaks = 0
        self.high = self.peak = 0
        self.entry = 0
        self.cooldown_until = -1
        self.halted = self.exiting = False
        self.was_held = False

    def step(self, state, batch):
        bar = next((b for b in batch['bars'] if b['symbol'] == SYMBOL), None)
        self.peak = max(self.peak, state.equity)
        if not state.warming_up and state.equity * 10000 <= self.peak * (10000 - DRAWDOWN_BPS):
            self.halted = True
        held = state.positions.get(SYMBOL)
        if self.was_held and not held:
            self.high = self.entry = 0
            self.exiting = False
            self.cooldown_until = state.seq + COOLDOWN
        self.was_held = bool(held)
        if bar is None:
            return []
        close = int(bar['c'])
        if close <= 0:
            return []
        self.count += 1
        self.closes.append(close)
        old_slow = self.slow
        if self.fast is None:
            self.fast = self.slow = close
        else:
            # Integer fixed-point EMA avoids platform-dependent floating arithmetic.
            self.fast += 2 * (close - self.fast) // (FAST + 1)
            self.slow += 2 * (close - self.slow) // (SLOW + 1)
        up = (self.count >= SLOW and self.fast * 10000 > self.slow * 10020
              and close > self.slow and self.slow > old_slow
              and close * 10000 > self.closes[0] * 10020)
        self.confirm = self.confirm + 1 if up else 0
        broken = self.fast * 10000 < self.slow * 9950 and close < self.slow
        self.breaks = self.breaks + 1 if broken else 0
        if state.warming_up:
            return []
        caps = state.hello['caps']
        if caps['max_orders_per_bar'] < 1:
            return []
        minimum = int(state.hello['fees']['min_notional_quote_units'])
        if held:
            if not self.entry:
                # Cost basis includes entry fees and impact; target a net cushion.
                scales = state.symbols[SYMBOL]
                self.entry = (held.cost * 10 ** (scales["qty_scale"] + scales["price_scale"])
                              // (held.qty * 10 ** state.hello["capital"]["quote_scale"]))
            self.high = max(self.high, close)
            if (self.halted or close * 10000 >= self.entry * (10000 + TAKE_PROFIT_BPS) or self.breaks >= CONFIRM
                    or close * 10000 <= self.high * (10000 - TRAIL_BPS)):
                self.exiting = True
            if self.exiting and state.value(SYMBOL, held.qty) >= minimum:
                return [{'side': 'sell', 'symbol': SYMBOL, 'qty': held.qty,
                         'max_slippage_bps': MAX_SLIPPAGE_BPS}]
            return []
        if (self.halted or state.seq < self.cooldown_until or self.confirm < CONFIRM
                or close <= self.closes[-6]
                or close * 10000 > self.fast * 10010
                or len(state.positions) >= caps['max_open_positions']):
            return []
        amount = min(state.cash, state.equity * WEIGHT_BPS // 10000,
                     state.weight_room(SYMBOL) * 99 // 100)
        # Avoid liquidity that consumes the signal's expected edge before entry.
        impact = state.impact_bps(SYMBOL, amount)
        if amount < max(1, minimum) or impact is None or impact > 10:
            return []
        return [{'side': 'buy', 'symbol': SYMBOL, 'notional_quote_units': amount,
                 'max_slippage_bps': MAX_SLIPPAGE_BPS}]


def on_batch(state, batch):
    if not hasattr(state, 'northstar'):
        state.northstar = Northstar()
    return state.northstar.step(state, batch)


if __name__ == '__main__':
    makefun_bars.run(on_batch)
