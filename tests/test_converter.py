"""Tests for vnpy.trader.converter — PositionHolding, OffsetConverter."""

from unittest.mock import MagicMock

from vnpy.trader.constant import Direction, Exchange, Offset, OrderType, Product, Status
from vnpy.trader.converter import OffsetConverter, PositionHolding
from vnpy.trader.object import (
    ContractData,
    OrderData,
    OrderRequest,
    PositionData,
    TradeData,
)


def _contract(
    symbol: str = "rb2501",
    exchange: Exchange = Exchange.SHFE,
    net_position: bool = False,
) -> ContractData:
    return ContractData(
        symbol=symbol,
        exchange=exchange,
        name="test",
        product=Product.FUTURES,
        size=10,
        pricetick=1.0,
        gateway_name="ctp",
        net_position=net_position,
    )


def _position(
    symbol: str = "rb2501",
    exchange: Exchange = Exchange.SHFE,
    direction: Direction = Direction.LONG,
    volume: float = 10,
    yd_volume: float = 5,
) -> PositionData:
    return PositionData(
        symbol=symbol,
        exchange=exchange,
        direction=direction,
        volume=volume,
        yd_volume=yd_volume,
        gateway_name="ctp",
    )


def _order(
    symbol: str = "rb2501",
    exchange: Exchange = Exchange.SHFE,
    direction: Direction = Direction.SHORT,
    offset: Offset = Offset.CLOSE,
    volume: float = 3,
    traded: float = 0,
    status: Status = Status.NOTTRADED,
    orderid: str = "o1",
) -> OrderData:
    return OrderData(
        symbol=symbol,
        exchange=exchange,
        orderid=orderid,
        direction=direction,
        offset=offset,
        volume=volume,
        traded=traded,
        status=status,
        gateway_name="ctp",
    )


def _trade(
    symbol: str = "rb2501",
    exchange: Exchange = Exchange.SHFE,
    direction: Direction = Direction.LONG,
    offset: Offset = Offset.OPEN,
    volume: float = 5,
) -> TradeData:
    return TradeData(
        symbol=symbol,
        exchange=exchange,
        orderid="o1",
        tradeid="t1",
        direction=direction,
        offset=offset,
        volume=volume,
        gateway_name="ctp",
    )


def _order_req(
    symbol: str = "rb2501",
    exchange: Exchange = Exchange.SHFE,
    direction: Direction = Direction.LONG,
    volume: float = 3,
    offset: Offset = Offset.CLOSE,
) -> OrderRequest:
    return OrderRequest(
        symbol=symbol,
        exchange=exchange,
        direction=direction,
        type=OrderType.LIMIT,
        volume=volume,
        price=3500,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# PositionHolding
# ---------------------------------------------------------------------------


class TestPositionHolding:
    def test_update_position_long(self) -> None:
        h = PositionHolding(_contract())
        h.update_position(_position(direction=Direction.LONG, volume=10, yd_volume=5))
        assert h.long_pos == 10
        assert h.long_yd == 5
        assert h.long_td == 5

    def test_update_position_short(self) -> None:
        h = PositionHolding(_contract())
        h.update_position(_position(direction=Direction.SHORT, volume=8, yd_volume=3))
        assert h.short_pos == 8
        assert h.short_yd == 3
        assert h.short_td == 5

    def test_update_trade_long_open(self) -> None:
        h = PositionHolding(_contract())
        h.update_trade(_trade(direction=Direction.LONG, offset=Offset.OPEN, volume=5))
        assert h.long_td == 5
        assert h.long_pos == 5

    def test_update_trade_long_close_shfe(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.SHFE))
        h.update_position(_position(direction=Direction.SHORT, volume=10, yd_volume=10))
        h.update_trade(
            _trade(
                direction=Direction.LONG,
                offset=Offset.CLOSE,
                volume=3,
                exchange=Exchange.SHFE,
            )
        )
        assert h.short_yd == 7

    def test_update_trade_long_close_non_shfe(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.CFFEX))
        h.update_position(
            _position(
                direction=Direction.SHORT,
                volume=10,
                yd_volume=5,
                exchange=Exchange.CFFEX,
            )
        )
        h.update_trade(
            _trade(
                direction=Direction.LONG,
                offset=Offset.CLOSE,
                volume=3,
                exchange=Exchange.CFFEX,
            )
        )
        assert h.short_td == 2

    def test_update_trade_short_open(self) -> None:
        h = PositionHolding(_contract())
        h.update_trade(_trade(direction=Direction.SHORT, offset=Offset.OPEN, volume=4))
        assert h.short_td == 4
        assert h.short_pos == 4

    def test_update_order_active(self) -> None:
        h = PositionHolding(_contract())
        order = _order(status=Status.NOTTRADED)
        h.update_order(order)
        assert order.vt_orderid in h.active_orders

    def test_update_order_inactive_removed(self) -> None:
        h = PositionHolding(_contract())
        order = _order(status=Status.NOTTRADED)
        h.update_order(order)
        finished = _order(status=Status.ALLTRADED)
        h.update_order(finished)
        assert finished.vt_orderid not in h.active_orders

    def test_convert_shfe_open(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.SHFE))
        req = _order_req(offset=Offset.OPEN)
        result = h.convert_order_request_shfe(req)
        assert len(result) == 1
        assert result[0].offset == Offset.OPEN

    def test_convert_shfe_close_td_only(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.SHFE))
        h.update_position(_position(direction=Direction.SHORT, volume=10, yd_volume=5))
        req = _order_req(direction=Direction.LONG, offset=Offset.CLOSE, volume=3)
        result = h.convert_order_request_shfe(req)
        assert len(result) == 1
        assert result[0].offset == Offset.CLOSETODAY

    def test_convert_shfe_close_split_td_yd(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.SHFE))
        h.update_position(_position(direction=Direction.SHORT, volume=10, yd_volume=5))
        req = _order_req(direction=Direction.LONG, offset=Offset.CLOSE, volume=8)
        result = h.convert_order_request_shfe(req)
        assert len(result) == 2
        offsets = {r.offset for r in result}
        assert Offset.CLOSETODAY in offsets
        assert Offset.CLOSEYESTERDAY in offsets

    def test_convert_shfe_volume_exceeds_available(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.SHFE))
        h.update_position(_position(direction=Direction.SHORT, volume=5, yd_volume=5))
        req = _order_req(direction=Direction.LONG, offset=Offset.CLOSE, volume=100)
        result = h.convert_order_request_shfe(req)
        assert result == []

    def test_convert_lock_with_td_volume_non_shfe(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.CFFEX))
        h.update_position(
            _position(
                direction=Direction.SHORT,
                volume=10,
                yd_volume=5,
                exchange=Exchange.CFFEX,
            )
        )
        req = _order_req(direction=Direction.LONG, offset=Offset.CLOSE, volume=3)
        result = h.convert_order_request_lock(req)
        assert len(result) == 1
        assert result[0].offset == Offset.OPEN

    def test_convert_lock_no_td_volume(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.CFFEX))
        h.update_position(
            _position(
                direction=Direction.SHORT,
                volume=5,
                yd_volume=5,
                exchange=Exchange.CFFEX,
            )
        )
        req = _order_req(direction=Direction.LONG, offset=Offset.CLOSE, volume=3)
        result = h.convert_order_request_lock(req)
        assert len(result) == 1
        assert result[0].offset == Offset.CLOSE
        assert result[0].volume == 3

    def test_convert_net_shfe(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.SHFE))
        h.update_position(_position(direction=Direction.SHORT, volume=10, yd_volume=5))
        req = _order_req(
            direction=Direction.LONG,
            offset=Offset.CLOSE,
            volume=8,
            exchange=Exchange.SHFE,
        )
        result = h.convert_order_request_net(req)
        offsets = [r.offset for r in result]
        assert Offset.CLOSETODAY in offsets
        assert Offset.CLOSEYESTERDAY in offsets

    def test_convert_net_non_shfe(self) -> None:
        h = PositionHolding(_contract(exchange=Exchange.CFFEX))
        h.update_position(
            _position(
                direction=Direction.SHORT,
                volume=10,
                yd_volume=5,
                exchange=Exchange.CFFEX,
            )
        )
        req = _order_req(
            direction=Direction.LONG,
            offset=Offset.CLOSE,
            volume=15,
            exchange=Exchange.CFFEX,
        )
        result = h.convert_order_request_net(req)
        offsets = [r.offset for r in result]
        assert Offset.CLOSE in offsets
        assert Offset.OPEN in offsets


# ---------------------------------------------------------------------------
# OffsetConverter
# ---------------------------------------------------------------------------


class TestOffsetConverter:
    def _make_converter(
        self,
        contract: ContractData | None = None,
    ) -> OffsetConverter:
        if contract is None:
            contract = _contract()
        engine = MagicMock()
        engine.get_contract = MagicMock(return_value=contract)
        return OffsetConverter(engine)

    def test_is_convert_required_true(self) -> None:
        oc = self._make_converter(_contract(net_position=False))
        assert oc.is_convert_required("rb2501.SHFE")

    def test_is_convert_required_false_net(self) -> None:
        oc = self._make_converter(_contract(net_position=True))
        assert not oc.is_convert_required("rb2501.SHFE")

    def test_is_convert_required_false_no_contract(self) -> None:
        engine = MagicMock()
        engine.get_contract = MagicMock(return_value=None)
        oc = OffsetConverter(engine)
        assert not oc.is_convert_required("unknown.SHFE")

    def test_convert_passthrough_for_net_position(self) -> None:
        oc = self._make_converter(_contract(net_position=True))
        req = _order_req(offset=Offset.CLOSE)
        result = oc.convert_order_request(req, lock=False)
        assert result == [req]

    def test_convert_shfe(self) -> None:
        oc = self._make_converter(_contract(exchange=Exchange.SHFE))
        oc.update_position(_position(direction=Direction.SHORT, volume=10, yd_volume=5))
        req = _order_req(direction=Direction.LONG, offset=Offset.CLOSE, volume=3)
        result = oc.convert_order_request(req, lock=False)
        assert len(result) == 1
        assert result[0].offset == Offset.CLOSETODAY

    def test_convert_lock(self) -> None:
        oc = self._make_converter(_contract(exchange=Exchange.CFFEX))
        oc.update_position(
            _position(
                direction=Direction.SHORT,
                volume=10,
                yd_volume=5,
                exchange=Exchange.CFFEX,
            )
        )
        req = _order_req(direction=Direction.LONG, offset=Offset.CLOSE, volume=3)
        result = oc.convert_order_request(req, lock=True)
        assert len(result) == 1
        assert result[0].offset == Offset.OPEN

    def test_update_trade(self) -> None:
        oc = self._make_converter()
        trade = _trade(direction=Direction.LONG, offset=Offset.OPEN, volume=5)
        oc.update_trade(trade)
        holding = oc.holdings.get("rb2501.SHFE")
        assert holding is not None
        assert holding.long_td == 5

    def test_update_order(self) -> None:
        oc = self._make_converter()
        order = _order(status=Status.NOTTRADED)
        oc.update_order(order)
        holding = oc.holdings.get("rb2501.SHFE")
        assert holding is not None
        assert order.vt_orderid in holding.active_orders

    def test_get_position_holding_creates(self) -> None:
        oc = self._make_converter()
        holding = oc.get_position_holding("rb2501.SHFE")
        assert holding is not None
        assert "rb2501.SHFE" in oc.holdings

    def test_get_position_holding_returns_none_no_contract(self) -> None:
        engine = MagicMock()
        engine.get_contract = MagicMock(return_value=None)
        oc = OffsetConverter(engine)
        holding = oc.get_position_holding("unknown.SHFE")
        assert holding is None
