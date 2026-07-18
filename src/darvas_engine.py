"""Darvas Box engine - pure mathematical logic (NO AI, NO chart vision)."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class State(str, Enum):
    SCANNING = "SCANNING"
    TOP_PENDING = "TOP_PENDING"
    BOTTOM_PENDING = "BOTTOM_PENDING"
    BOX_CONFIRMED = "BOX_CONFIRMED"
    IN_POSITION = "IN_POSITION"


@dataclass
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Event:
    type: str
    date: str
    symbol: str
    data: dict = field(default_factory=dict)


class DarvasEngine:
    def __init__(self, symbol, confirm_days=3, high_lookback=252, vol_window=50,
                 vol_mult=2.0, breakout_buffer=0.001, require_volume=True, trail_every=1):
        self.symbol = symbol
        self.confirm_days = confirm_days
        self.high_lookback = high_lookback
        self.vol_window = vol_window
        self.vol_mult = vol_mult
        self.buffer = breakout_buffer
        self.require_volume = require_volume
        self.trail_every = trail_every
        self._trail_box_num = 0
        self.state = State.SCANNING
        self.top_high = None
        self.top_count = 0
        self.bottom_low = None
        self.bottom_count = 0
        self.box_top = None
        self.box_bottom = None
        self.entry_price = None
        self.stop_price = None
        self._highs = []
        self._lows = []
        self._vols = []

    def _prior_high(self):
        w = self._highs[-self.high_lookback:]
        return max(w) if w else None

    def _avg_vol(self):
        w = self._vols[-self.vol_window:]
        return sum(w) / len(w) if w else None

    def _volume_ok(self, bar):
        if not self.require_volume:
            return True
        avg = self._avg_vol()
        if avg is None or avg == 0:
            return False
        return bar.volume >= self.vol_mult * avg

    def _reset(self):
        self.state = State.SCANNING
        self.top_high = None
        self.top_count = 0
        self.bottom_low = None
        self.bottom_count = 0
        self.box_top = self.box_bottom = None
        self.entry_price = self.stop_price = None
        self._trail_box_num = 0

    def process_bar(self, bar):
        ev = []
        has_hist = len(self._highs) >= min(self.vol_window, 20)
        if self.state == State.SCANNING:
            ph = self._prior_high()
            if has_hist and ph is not None and bar.high > ph and self._volume_ok(bar):
                self.state = State.TOP_PENDING
                self.top_high = bar.high
                self.top_count = 0
        elif self.state == State.TOP_PENDING:
            if bar.high > self.top_high:
                self.top_high = bar.high
                self.top_count = 0
            else:
                self.top_count += 1
                if self.top_count >= self.confirm_days:
                    self.state = State.BOTTOM_PENDING
                    self.bottom_low = min(self._lows[-self.confirm_days:] + [bar.low])
                    self.bottom_count = 0
        elif self.state == State.BOTTOM_PENDING:
            if bar.high > self.top_high:
                self.state = State.TOP_PENDING
                self.top_high = bar.high
                self.top_count = 0
                self.bottom_low = None
                self.bottom_count = 0
            elif bar.low < self.bottom_low:
                self.bottom_low = bar.low
                self.bottom_count = 0
            else:
                self.bottom_count += 1
                if self.bottom_count >= self.confirm_days:
                    self.box_top = self.top_high
                    self.box_bottom = self.bottom_low
                    self.entry_price = round(self.box_top * (1 + self.buffer), 4)
                    self.stop_price = round(self.box_bottom * (1 - self.buffer), 4)
                    self.state = State.BOX_CONFIRMED
                    ev.append(Event("BOX_CONFIRMED", bar.date, self.symbol,
                        {"top": self.box_top, "bottom": self.box_bottom,
                         "entry": self.entry_price, "stop": self.stop_price}))
        elif self.state == State.BOX_CONFIRMED:
            if bar.high >= self.entry_price:
                self.state = State.IN_POSITION
                ev.append(Event("BREAKOUT", bar.date, self.symbol,
                    {"entry": self.entry_price, "stop": self.stop_price,
                     "box_top": self.box_top, "box_bottom": self.box_bottom}))
                self.top_high = self.box_top
                self.top_count = 0
                self.bottom_low = None
                self.bottom_count = 0
            elif bar.low <= self.stop_price:
                ev.append(Event("BOX_BROKEN", bar.date, self.symbol, {"stop": self.stop_price}))
                self._reset()
        elif self.state == State.IN_POSITION:
            if bar.low <= self.stop_price:
                ev.append(Event("STOPPED_OUT", bar.date, self.symbol, {"stop": self.stop_price}))
                self._reset()
            else:
                ev += self._trail(bar)
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        self._vols.append(bar.volume)
        return ev

    def _trail(self, bar):
        ev = []
        if self.top_count == 0 and self.top_high is not None and bar.high > self.top_high:
            self.top_high = bar.high
            return ev
        if self.bottom_low is None:
            if bar.high > self.top_high:
                self.top_high = bar.high
                self.top_count = 0
            else:
                self.top_count += 1
                if self.top_count >= self.confirm_days:
                    self.bottom_low = min(self._lows[-self.confirm_days:] + [bar.low])
                    self.bottom_count = 0
        else:
            if bar.high > self.top_high:
                self.top_high = bar.high
                self.top_count = 0
                self.bottom_low = None
                self.bottom_count = 0
            elif bar.low < self.bottom_low:
                self.bottom_low = bar.low
                self.bottom_count = 0
            else:
                self.bottom_count += 1
                if self.bottom_count >= self.confirm_days:
                    self._trail_box_num += 1
                    do_raise = self.trail_every > 0 and (self._trail_box_num % self.trail_every == 0)
                    if do_raise:
                        new_stop = round(self.bottom_low * (1 - self.buffer), 4)
                        if new_stop > self.stop_price:
                            old = self.stop_price
                            self.stop_price = new_stop
                            ev.append(Event("STOP_RAISED", bar.date, self.symbol,
                                {"old_stop": old, "new_stop": new_stop, "new_box_bottom": self.bottom_low}))
                    self.top_count = 0
                    self.bottom_low = None
                    self.bottom_count = 0
        return ev


def run_series(symbol, bars, **kw):
    eng = DarvasEngine(symbol, **kw)
    out = []
    for b in bars:
        out += eng.process_bar(b)
    return out
