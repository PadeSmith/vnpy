"""Tests for vnpy.trader.object — data classes, post_init, helper methods."""

from datetime import datetime

from vnpy.trader.constant import (
    Direction,
    Exchange,
    Interval,
    Offset,
    OrderType,
    Product,
    Status,
)
from vnpy.trader.object import (
    ACTIVE_STATUSES,
    AccountData,
    BarData,
    BaseData,
    CancelRequest,
    ContractData,
    HistoryRequest,
    LogData,
    OrderData,
    OrderRequest,
    PositionData,
    QuoteData,
    QuoteRequest,
    SubscribeRequest,
    TickData,
    TradeData,
)


NOW = datetime(2024, 1, 15, 10, 30, 0)


class TestBaseData:
    def test_extra_default_none(self) -> None:
        bd = BaseData(gateway_name="test")
        assert bd.extra is None


class TestTickData:
    def test_vt_symbol(self) -> None:
        t = TickData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            datetime=NOW,
            gateway_name="ctp",
        )
        assert t.vt_symbol == "rb2501.SHFE"

    def test_defaults(self) -> None:
        t = TickData(
            symbol="IF2501",
            exchange=Exchange.CFFEX,
            datetime=NOW,
            gateway_name="ctp",
        )
        assert t.last_price == 0
        assert t.volume == 0
        assert t.localtime is None


class TestBarData:
    def test_vt_symbol(self) -> None:
        b = BarData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            datetime=NOW,
            gateway_name="ctp",
        )
        assert b.vt_symbol == "rb2501.SHFE"

    def test_interval_default(self) -> None:
        b = BarData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            datetime=NOW,
            gateway_name="ctp",
        )
        assert b.interval is None


class TestOrderData:
    def _make_order(self, status: Status = Status.SUBMITTING) -> OrderData:
        return OrderData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            orderid="001",
            gateway_name="ctp",
            status=status,
        )

    def test_vt_fields(self) -> None:
        o = self._make_order()
        assert o.vt_symbol == "rb2501.SHFE"
        assert o.vt_orderid == "ctp.001"

    def test_is_active_submitting(self) -> None:
        assert self._make_order(Status.SUBMITTING).is_active()

    def test_is_active_nottraded(self) -> None:
        assert self._make_order(Status.NOTTRADED).is_active()

    def test_is_active_parttraded(self) -> None:
        assert self._make_order(Status.PARTTRADED).is_active()

    def test_not_active_alltraded(self) -> None:
        assert not self._make_order(Status.ALLTRADED).is_active()

    def test_not_active_cancelled(self) -> None:
        assert not self._make_order(Status.CANCELLED).is_active()

    def test_not_active_rejected(self) -> None:
        assert not self._make_order(Status.REJECTED).is_active()

    def test_create_cancel_request(self) -> None:
        o = self._make_order()
        req = o.create_cancel_request()
        assert isinstance(req, CancelRequest)
        assert req.orderid == "001"
        assert req.symbol == "rb2501"
        assert req.exchange == Exchange.SHFE

    def test_active_statuses_set(self) -> None:
        assert ACTIVE_STATUSES == {
            Status.SUBMITTING,
            Status.NOTTRADED,
            Status.PARTTRADED,
        }


class TestTradeData:
    def test_vt_fields(self) -> None:
        t = TradeData(
            symbol="IF2501",
            exchange=Exchange.CFFEX,
            orderid="o1",
            tradeid="t1",
            gateway_name="ctp",
        )
        assert t.vt_symbol == "IF2501.CFFEX"
        assert t.vt_orderid == "ctp.o1"
        assert t.vt_tradeid == "ctp.t1"


class TestPositionData:
    def test_vt_positionid(self) -> None:
        p = PositionData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            gateway_name="ctp",
        )
        assert p.vt_positionid == "ctp.rb2501.SHFE.多"


class TestAccountData:
    def test_available(self) -> None:
        a = AccountData(
            accountid="test",
            balance=100000,
            frozen=30000,
            gateway_name="ctp",
        )
        assert a.available == 70000.0
        assert a.vt_accountid == "ctp.test"


class TestLogData:
    def test_time_auto_set(self) -> None:
        lg = LogData(msg="hello", gateway_name="ctp")
        assert lg.msg == "hello"
        assert isinstance(lg.time, datetime)


class TestContractData:
    def test_vt_symbol(self) -> None:
        c = ContractData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            name="螺纹钢2501",
            product=Product.FUTURES,
            size=10,
            pricetick=1.0,
            gateway_name="ctp",
        )
        assert c.vt_symbol == "rb2501.SHFE"


class TestQuoteData:
    def test_vt_fields(self) -> None:
        q = QuoteData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            quoteid="q1",
            gateway_name="ctp",
        )
        assert q.vt_symbol == "rb2501.SHFE"
        assert q.vt_quoteid == "ctp.q1"

    def test_is_active(self) -> None:
        q = QuoteData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            quoteid="q1",
            gateway_name="ctp",
            status=Status.SUBMITTING,
        )
        assert q.is_active()

    def test_create_cancel_request(self) -> None:
        q = QuoteData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            quoteid="q1",
            gateway_name="ctp",
        )
        req = q.create_cancel_request()
        assert req.orderid == "q1"


class TestSubscribeRequest:
    def test_vt_symbol(self) -> None:
        sr = SubscribeRequest(symbol="rb2501", exchange=Exchange.SHFE)
        assert sr.vt_symbol == "rb2501.SHFE"


class TestOrderRequest:
    def test_vt_symbol(self) -> None:
        req = OrderRequest(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=1,
            price=3500,
        )
        assert req.vt_symbol == "rb2501.SHFE"

    def test_create_order_data(self) -> None:
        req = OrderRequest(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=10,
            price=3500,
            offset=Offset.OPEN,
        )
        order = req.create_order_data("order1", "ctp")
        assert isinstance(order, OrderData)
        assert order.orderid == "order1"
        assert order.gateway_name == "ctp"
        assert order.volume == 10
        assert order.price == 3500
        assert order.offset == Offset.OPEN
        assert order.direction == Direction.LONG


class TestCancelRequest:
    def test_vt_symbol(self) -> None:
        cr = CancelRequest(orderid="001", symbol="rb2501", exchange=Exchange.SHFE)
        assert cr.vt_symbol == "rb2501.SHFE"


class TestHistoryRequest:
    def test_vt_symbol(self) -> None:
        hr = HistoryRequest(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            start=NOW,
            interval=Interval.MINUTE,
        )
        assert hr.vt_symbol == "rb2501.SHFE"


class TestQuoteRequest:
    def test_vt_symbol_and_create_quote_data(self) -> None:
        qr = QuoteRequest(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            bid_price=3500,
            bid_volume=1,
            ask_price=3501,
            ask_volume=1,
        )
        assert qr.vt_symbol == "rb2501.SHFE"

        quote = qr.create_quote_data("q1", "ctp")
        assert isinstance(quote, QuoteData)
        assert quote.bid_price == 3500
        assert quote.ask_price == 3501
