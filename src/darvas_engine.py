"""
Darvas Box engine - pure mathematical logic (NO AI, NO chart vision).
Fed bars one day at a time (EOD), returns a list of Events.
"""
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

    def __repr__(self):
        return f"Event({self.type} {self.symbol} {self.date} {self.data})"


class DarvasEngine:
    def __init__(
        self,
        symbol: str,
        confirm_days: int = 3,
        high_lookback: int = 252,
        vol_window: int = 50,
        vol_mult: float = 2.0,
        breakout_buffer: float = 0.001,
        require_volume: bool = True,
    ):
        self.symbol = symbol
        self.confirm_days = confirm_days
        self.high_lookback = high_lookback
        self.vol_window = vol_window
        self.vol_mult = vol_mult
        self.buffer = breakout_buffer
        self.require_volume = require_volume

        self.state = State.SCANNING
        self.top_high: Optional[float] = None
        self.top_count = 0
        self.bottom_low: Optional[float] = None
        self.bottom_count = 0
        self.box_top: Optional[float] = None
        self.box_bottom: Optional[float] = None
        self.entry_price: Optional[float] = None
        self.stop_price: Optional[float] = None

        self._highs: List[float] = []
        self._lows: List[float] = []
        self._vols: List[float] = []

    def _prior_high(self) -> Optional[float]:
        window = self._highs[-self.high_lookback:]
        return max(window) if window else None

    def _avg_vol(self) -> Optional[float]:
        window = self._vols[-self.vol_window:]
        return sum(window) / len(window) if window else None

    def _volume_ok(self, bar: Bar) -> bool:
        if not self.require_volume:
            return True
        avg = self._avg_vol()
        if avg is None or avg == 0:
            return False
        return bar.volume >= self.vol_mult * avg

    def _reset_to_scanning(self):
        self.state = State.SCANNING
        self.top_high = None
        self.top_count = 0
        self.bottom_low = None
        self.bottom_count = 0
        self.box_top = self.box_bottom = None
        self.entry_price = self.stop_price = None

    def process_bar(self, bar: Bar) -> List[Event]:
        events: List[Event] = []
        has_history = len(self._highs) >= min(self.vol_window, 20)

        if self.state == State.SCANNING:
            prior_high = self._prior_high()
            if (
                has_history
                and prior_high is not None
                and bar.high > prior_high
                and self._volume_ok(bar)
            ):
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
                    recent_lows = self._lows[-self.confirm_days:] + [bar.low]
                    self.bottom_low = min(recent_lows)
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
                    events.append(Event(
                        "BOX_CONFIRMED", bar.date, self.symbol,
                        {"top": self.box_top, "bottom": self.box_bottom,
                         "entry": self.entry_price, "stop": self.stop_price},
                    ))

        elif self.state == State.BOX_CONFIRMED:
            if bar.high >= self.entry_price:
                self.state = State.IN_POSITION
                events.append(Event(
                    "BREAKOUT", bar.date, self.symbol,
                    {"entry": self.entry_price, "stop": self.stop_price,
                     "box_top": self.box_top, "box_bottom": self.box_bottom},
                ))
                self.top_high = self.box_top
                self.top_count = 0
                self.bottom_low = None
                self.bottom_count = 0
            elif bar.low <= self.stop_price:
                events.append(Event(
                    "BOX_BROKEN", bar.date, self.symbol,
                    {"stop": self.stop_price},
                ))
                self._reset_to_scanning()

        elif self.state == State.IN_POSITION:
            if bar.low <= self.stop_price:
                events.append(Event(
                    "STOPPED_OUT", bar.date, self.symbol,
                    {"stop": self.stop_price},
                ))
                self._reset_to_scanning()
            else:
                events += self._trail(bar)

        self._highs.append(bar.high)
        self._lows.append(bar.low)
        self._vols.append(bar.volume)
        return events

    def _trail(self, bar: Bar) -> List[Event]:
        events: List[Event] = []
        if self.top_count == 0 and self.top_high is not None and bar.high > self.top_high:
            self.top_high = bar.high
            return events
        if self.bottom_low is None:
            if bar.high > self.top_high:
                self.top_high = bar.high
                self.top_count = 0
            else:
                self.top_count += 1
                if self.top_count >= self.confirm_days:
                    recent_lows = self._lows[-self.confirm_days:] + [bar.low]
                    self.bottom_low = min(recent_lows)
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
                    new_stop = round(self.bottom_low * (1 - self.buffer), 4)
                    if new_stop > self.stop_price:
                        old = self.stop_price
                        self.stop_price = new_stop
                        events.append(Event(
                            "STOP_RAISED", bar.date, self.symbol,
                            {"old_stop": old, "new_stop": new_stop,
                             "new_box_bottom": self.bottom_low},
                        ))
                    self.top_count = 0
                    self.bottom_low = None
                    self.bottom_count = 0
        return events

    def snapshot(self) -> dict:
        return {
            "symbol": self.symbol,
            "state": self.state.value,
            "top_high": self.top_high,
            "bottom_low": self.bottom_low,
            "top_count": self.top_count,
            "bottom_count": self.bottom_count,
            "entry_price": self.entry_price,
            "stop_price": self.stop_price,
        }


def run_series(symbol: str, bars: List[Bar], **kwargs) -> List[Event]:
    eng = DarvasEngine(symbol, **kwargs)
    out: List[Event] = []
    for b in bars:
        out += eng.process_bar(b)
    return out
