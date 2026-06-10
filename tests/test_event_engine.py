"""Tests for vnpy.event.engine — Event, EventEngine."""

import time

from vnpy.event.engine import Event, EventEngine, EVENT_TIMER


class TestEvent:
    def test_event_attributes(self) -> None:
        e = Event("test_type", data={"key": 1})
        assert e.type == "test_type"
        assert e.data == {"key": 1}

    def test_event_default_data_is_none(self) -> None:
        e = Event("t")
        assert e.data is None


class TestEventEngine:
    def test_register_and_process(self) -> None:
        engine = EventEngine(interval=60)
        engine.start()

        results: list[str] = []
        engine.register("test", lambda e: results.append(e.data))
        engine.put(Event("test", "hello"))

        time.sleep(0.5)
        engine.stop()

        assert results == ["hello"]

    def test_unregister(self) -> None:
        engine = EventEngine(interval=60)
        engine.start()

        results: list[str] = []
        handler = lambda e: results.append(e.data)  # noqa: E731
        engine.register("test", handler)
        engine.unregister("test", handler)

        engine.put(Event("test", "should_not_appear"))
        time.sleep(0.5)
        engine.stop()

        assert results == []

    def test_duplicate_register_ignored(self) -> None:
        engine = EventEngine(interval=60)
        handler = lambda e: None  # noqa: E731
        engine.register("t", handler)
        engine.register("t", handler)
        assert len(engine._handlers["t"]) == 1
        engine.start()
        engine.stop()

    def test_general_handler(self) -> None:
        engine = EventEngine(interval=60)
        engine.start()

        results: list[str] = []
        engine.register_general(lambda e: results.append(e.type))

        engine.put(Event("type_a"))
        engine.put(Event("type_b"))
        time.sleep(0.5)
        engine.stop()

        assert "type_a" in results
        assert "type_b" in results

    def test_unregister_general(self) -> None:
        engine = EventEngine(interval=60)
        engine.start()

        results: list[str] = []
        handler = lambda e: results.append(e.type)  # noqa: E731
        engine.register_general(handler)
        engine.unregister_general(handler)

        engine.put(Event("test"))
        time.sleep(0.5)
        engine.stop()

        assert results == []

    def test_timer_event_generated(self) -> None:
        engine = EventEngine(interval=1)
        results: list[str] = []
        engine.register(EVENT_TIMER, lambda e: results.append(e.type))
        engine.start()
        time.sleep(2.5)
        engine.stop()
        assert len(results) >= 1
        assert all(r == EVENT_TIMER for r in results)

    def test_multiple_handlers_same_type(self) -> None:
        engine = EventEngine(interval=60)
        engine.start()

        results_a: list[str] = []
        results_b: list[str] = []
        engine.register("t", lambda e: results_a.append(e.data))
        engine.register("t", lambda e: results_b.append(e.data))

        engine.put(Event("t", "val"))
        time.sleep(0.5)
        engine.stop()

        assert results_a == ["val"]
        assert results_b == ["val"]
