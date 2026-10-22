"""Unit tests for SqliteEventFeed persistent event store and replay."""

import asyncio
from pathlib import Path

import pytest

from agency.domain.events import PlanningCompleted, RunStarted
from agency.infrastructure.persistence.sqlite_event_feed import SqliteEventFeed


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    """Provide a temporary SQLite database file path."""
    return tmp_path / "events.db"


def test_record_and_get_events(db_file: Path) -> None:
    feed = SqliteEventFeed(db_path=db_file)
    event1 = RunStarted(run_id="run-1", project_id="proj-alpha")
    event2 = PlanningCompleted(run_id="run-1", spec_id="spec-123")

    env1 = feed.record_event(event1)
    env2 = feed.record_event(event2)

    events = feed.get_events(run_id="run-1")
    assert len(events) == 2
    assert events[0].event_id == env1.event_id
    assert events[0].event_type == "RunStarted"
    assert events[0].payload["project_id"] == "proj-alpha"
    assert events[1].event_id == env2.event_id
    assert events[1].event_type == "PlanningCompleted"
    assert events[1].payload["spec_id"] == "spec-123"


def test_cursor_replay_with_after_id(db_file: Path) -> None:
    feed = SqliteEventFeed(db_path=db_file)
    e1 = feed.record_event(RunStarted(run_id="run-cursor", project_id="p1"))
    e2 = feed.record_event(PlanningCompleted(run_id="run-cursor", spec_id="s1"))
    e3 = feed.record_event(PlanningCompleted(run_id="run-cursor", spec_id="s2"))

    replayed = feed.get_events(run_id="run-cursor", after_id=e1.event_id)
    assert len(replayed) == 2
    assert [ev.event_id for ev in replayed] == [e2.event_id, e3.event_id]

    replayed_last = feed.get_events(run_id="run-cursor", after_id=e3.event_id)
    assert len(replayed_last) == 0


def test_run_isolation(db_file: Path) -> None:
    feed = SqliteEventFeed(db_path=db_file)
    e_run1 = feed.record_event(RunStarted(run_id="run-A", project_id="A"))
    feed.record_event(RunStarted(run_id="run-B", project_id="B"))

    events_a = feed.get_events(run_id="run-A")
    assert len(events_a) == 1
    assert events_a[0].event_id == e_run1.event_id


def test_durability_across_instances(db_file: Path) -> None:
    feed1 = SqliteEventFeed(db_path=db_file)
    e1 = feed1.record_event(RunStarted(run_id="run-durable", project_id="proj-durable"))

    # Instantiate new feed on same db file (simulating server reboot)
    feed2 = SqliteEventFeed(db_path=db_file)
    persisted = feed2.get_events(run_id="run-durable")

    assert len(persisted) == 1
    assert persisted[0].event_id == e1.event_id
    assert persisted[0].payload["project_id"] == "proj-durable"


def test_live_subscriber_queue(db_file: Path) -> None:
    async def _run() -> None:
        feed = SqliteEventFeed(db_path=db_file)
        queue = feed.subscribe("run-live")

        event = RunStarted(run_id="run-live", project_id="proj-live")
        envelope = feed.record_event(event)

        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.event_id == envelope.event_id

        feed.unsubscribe("run-live", queue)
        assert "run-live" not in feed._subscribers

    asyncio.run(_run())
