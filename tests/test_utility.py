"""Tests for vnpy.trader.utility — pure functions, BarGenerator, ArrayManager."""

from datetime import datetime, time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import (
    ArrayManager,
    BarGenerator,
    ceil_to,
    extract_vt_symbol,
    floor_to,
    generate_vt_symbol,
    get_digits,
    get_icon_path,
    load_json,
    round_to,
    save_json,
    virtual,
)


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


class TestExtractVtSymbol:
    def test_basic(self) -> None:
        sym, exc = extract_vt_symbol("rb2501.SHFE")
        assert sym == "rb2501"
        assert exc == Exchange.SHFE

    def test_symbol_with_dots(self) -> None:
        sym, exc = extract_vt_symbol("BRK.B.NYSE")
        assert sym == "BRK.B"
        assert exc == Exchange.NYSE


class TestGenerateVtSymbol:
    def test_basic(self) -> None:
        assert generate_vt_symbol("rb2501", Exchange.SHFE) == "rb2501.SHFE"


class TestRoundTo:
    def test_round_to_pricetick(self) -> None:
        assert round_to(3.456, 0.05) == 3.45

    def test_round_to_integer(self) -> None:
        assert round_to(123.7, 1) == 124.0

    def test_round_to_small_tick(self) -> None:
        assert round_to(0.000156, 0.0001) == 0.0002


class TestFloorTo:
    def test_floor(self) -> None:
        assert floor_to(3.456, 0.05) == 3.45

    def test_floor_exact(self) -> None:
        assert floor_to(3.45, 0.05) == 3.45


class TestCeilTo:
    def test_ceil(self) -> None:
        assert ceil_to(3.411, 0.05) == 3.45

    def test_ceil_exact(self) -> None:
        assert ceil_to(3.45, 0.05) == 3.45


class TestGetDigits:
    def test_integer(self) -> None:
        assert get_digits(100) == 0

    def test_float(self) -> None:
        assert get_digits(1.23) == 2

    def test_scientific(self) -> None:
        assert get_digits(1e-5) == 5


class TestJsonIO:
    def test_save_and_load(self, tmp_path: Path) -> None:
        with patch("vnpy.trader.utility.get_file_path", side_effect=lambda f: tmp_path / f):
            save_json("test.json", {"key": "value"})
            data = load_json("test.json")
            assert data == {"key": "value"}

    def test_load_nonexistent_creates_empty(self, tmp_path: Path) -> None:
        with patch("vnpy.trader.utility.get_file_path", side_effect=lambda f: tmp_path / f):
            data = load_json("missing.json")
            assert data == {}
            assert (tmp_path / "missing.json").exists()


class TestGetIconPath:
    def test_returns_path(self) -> None:
        result = get_icon_path("/some/dir/widget.py", "logo.ico")
        assert result.endswith("ico/logo.ico")


class TestVirtualDecorator:
    def test_virtual(self) -> None:
        @virtual
        def my_func() -> int:
            return 42

        assert my_func() == 42


# ---------------------------------------------------------------------------
# BarGenerator
# ---------------------------------------------------------------------------


def _make_tick(
    dt: datetime,
    price: float = 100.0,
    volume: float = 1000.0,
    turnover: float = 0.0,
) -> TickData:
    return TickData(
        symbol="rb2501",
        exchange=Exchange.SHFE,
        datetime=dt,
        gateway_name="test",
        last_price=price,
        volume=volume,
        turnover=turnover,
        open_interest=5000,
    )


def _make_bar(
    dt: datetime,
    o: float = 100,
    h: float = 105,
    lo: float = 95,
    c: float = 102,
    vol: float = 500,
    turnover: float = 0,
) -> BarData:
    return BarData(
        symbol="rb2501",
        exchange=Exchange.SHFE,
        datetime=dt,
        gateway_name="test",
        interval=Interval.MINUTE,
        open_price=o,
        high_price=h,
        low_price=lo,
        close_price=c,
        volume=vol,
        turnover=turnover,
        open_interest=1000,
    )


class TestBarGeneratorTick:
    def test_tick_to_1min_bar(self) -> None:
        bars: list[BarData] = []
        bg = BarGenerator(on_bar=bars.append)

        bg.update_tick(_make_tick(datetime(2024, 1, 1, 10, 0, 0), price=100, volume=0))
        bg.update_tick(_make_tick(datetime(2024, 1, 1, 10, 0, 30), price=105, volume=100))
        bg.update_tick(_make_tick(datetime(2024, 1, 1, 10, 1, 0), price=102, volume=200))

        assert len(bars) == 1
        assert bars[0].open_price == 100
        assert bars[0].close_price == 105
        assert bars[0].high_price == 105

    def test_zero_price_tick_filtered(self) -> None:
        bars: list[BarData] = []
        bg = BarGenerator(on_bar=bars.append)
        bg.update_tick(_make_tick(datetime(2024, 1, 1, 10, 0, 0), price=0))
        assert bg.bar is None

    def test_generate(self) -> None:
        bars: list[BarData] = []
        bg = BarGenerator(on_bar=bars.append)
        bg.update_tick(_make_tick(datetime(2024, 1, 1, 10, 0, 0), price=100, volume=0))
        result = bg.generate()
        assert result is not None
        assert len(bars) == 1

    def test_generate_when_empty(self) -> None:
        bars: list[BarData] = []
        bg = BarGenerator(on_bar=bars.append)
        assert bg.generate() is None


class TestBarGeneratorMinuteWindow:
    def test_5min_window(self) -> None:
        window_bars: list[BarData] = []
        bg = BarGenerator(
            on_bar=lambda b: None,
            window=5,
            on_window_bar=window_bars.append,
            interval=Interval.MINUTE,
        )

        for minute in range(10):
            bar = _make_bar(datetime(2024, 1, 1, 10, minute))
            bg.update_bar(bar)

        assert len(window_bars) == 2


class TestBarGeneratorHourWindow:
    def test_hour_bar(self) -> None:
        window_bars: list[BarData] = []
        bg = BarGenerator(
            on_bar=lambda b: None,
            window=1,
            on_window_bar=window_bars.append,
            interval=Interval.HOUR,
        )

        for hour in range(10, 12):
            for minute in range(60):
                bar = _make_bar(datetime(2024, 1, 1, hour, minute))
                bg.update_bar(bar)

        assert len(window_bars) >= 2

    def test_2hour_window(self) -> None:
        window_bars: list[BarData] = []
        bg = BarGenerator(
            on_bar=lambda b: None,
            window=2,
            on_window_bar=window_bars.append,
            interval=Interval.HOUR,
        )

        for hour in range(10, 14):
            for minute in range(60):
                bar = _make_bar(datetime(2024, 1, 1, hour, minute))
                bg.update_bar(bar)

        assert len(window_bars) >= 2


class TestBarGeneratorDailyWindow:
    def test_daily_bar(self) -> None:
        window_bars: list[BarData] = []
        daily_end = time(15, 0)
        bg = BarGenerator(
            on_bar=lambda b: None,
            window=1,
            on_window_bar=window_bars.append,
            interval=Interval.DAILY,
            daily_end=daily_end,
        )

        for minute in range(0, 60):
            bar = _make_bar(datetime(2024, 1, 1, 14, minute))
            bg.update_bar(bar)

        bar = _make_bar(datetime(2024, 1, 1, 15, 0))
        bg.update_bar(bar)

        assert len(window_bars) == 1

    def test_daily_requires_daily_end(self) -> None:
        with pytest.raises(RuntimeError):
            BarGenerator(
                on_bar=lambda b: None,
                window=1,
                on_window_bar=lambda b: None,
                interval=Interval.DAILY,
            )


# ---------------------------------------------------------------------------
# ArrayManager
# ---------------------------------------------------------------------------


def _fill_am(am: ArrayManager, n: int = 110) -> None:
    np.random.seed(42)
    for i in range(n):
        bar = BarData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            datetime=datetime(2024, 1, 1, 10, i % 60),
            gateway_name="test",
            open_price=100 + np.random.randn(),
            high_price=105 + abs(np.random.randn()),
            low_price=95 - abs(np.random.randn()),
            close_price=100 + np.random.randn(),
            volume=float(np.random.randint(100, 1000)),
            turnover=float(np.random.randint(1000, 10000)),
            open_interest=5000.0,
        )
        am.update_bar(bar)


class TestArrayManager:
    def test_not_inited_until_full(self) -> None:
        am = ArrayManager(size=5)
        assert not am.inited
        for i in range(5):
            bar = _make_bar(datetime(2024, 1, 1, 10, i))
            am.update_bar(bar)
        assert am.inited

    def test_properties(self) -> None:
        am = ArrayManager(size=10)
        _fill_am(am, 10)
        assert len(am.open) == 10
        assert len(am.high) == 10
        assert len(am.low) == 10
        assert len(am.close) == 10
        assert len(am.volume) == 10
        assert len(am.turnover) == 10
        assert len(am.open_interest) == 10

    def test_sma(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        val = am.sma(10)
        assert isinstance(val, float)
        arr = am.sma(10, array=True)
        assert isinstance(arr, np.ndarray)

    def test_ema(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        val = am.ema(10)
        assert isinstance(val, float)

    def test_rsi(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        val = am.rsi(14)
        assert isinstance(val, float)
        assert 0 <= val <= 100

    def test_macd(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        macd, signal, hist = am.macd(12, 26, 9)
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert isinstance(hist, float)

    def test_boll(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        upper, lower = am.boll(20, 2.0)
        assert isinstance(upper, float)
        assert isinstance(lower, float)
        assert upper > lower

    def test_atr(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        val = am.atr(14)
        assert isinstance(val, float)
        assert val > 0

    def test_cci(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        val = am.cci(14)
        assert isinstance(val, float)

    def test_keltner(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        upper, lower = am.keltner(20, 2.0)
        assert isinstance(upper, float)
        assert isinstance(lower, float)

    def test_donchian(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        upper, lower = am.donchian(20)
        assert isinstance(upper, float)
        assert isinstance(lower, float)
        assert upper >= lower

    def test_aroon(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        up, down = am.aroon(14)
        assert isinstance(up, float)
        assert isinstance(down, float)

    def test_adx(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        val = am.adx(14)
        assert isinstance(val, float)

    def test_bop(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        val = am.bop()
        assert isinstance(val, float)

    def test_stoch(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        k, d = am.stoch(5, 3, 0, 3, 0)
        assert isinstance(k, float)
        assert isinstance(d, float)

    def test_array_mode(self) -> None:
        am = ArrayManager(size=100)
        _fill_am(am, 110)
        arr = am.ema(10, array=True)
        assert isinstance(arr, np.ndarray)
        assert len(arr) == 100
