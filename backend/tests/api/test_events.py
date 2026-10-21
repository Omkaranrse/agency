"""API tests for Server-Sent Events (SSE) streaming and durable event replay."""

import pytest
from httpx import ASGITransport, AsyncClient

from agency.domain.entities.run import Run
from agency.domain.events import PlanningCompleted, PrototypeReady, RunStarted
from tests.api.conftest import TEST_API_KEY, APITestHarness, make_sample_brief


@pytest.mark.anyio
async def test_stream_events_content_type_and_headers(harness: APITestHarness) -> None:
    """SSE endpoint returns text/event-stream with no-cache and keep-alive headers."""
    brief = make_sample_brief()
    run = Run(run_id="run-sse-1", project_id="elena-sse-1", brief=brief)
    harness.repository.save(run)

    async with AsyncClient(
        transport=ASGITransport(app=harness.app),
        base_url="http://testserver",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        async with ac.stream("GET", "/api/v1/runs/run-sse-1/events") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"


@pytest.mark.anyio
async def test_stream_events_replays_history_from_last_event_id(
    harness: APITestHarness,
) -> None:
    """Historical events after Last-Event-ID are replayed in order with event IDs."""
    brief = make_sample_brief()
    run = Run(run_id="run-sse-2", project_id="elena-sse-2", brief=brief)
    harness.repository.save(run)

    # Record 3 events into durable feed
    e1 = harness.event_feed.record_event(
        RunStarted(run_id="run-sse-2", project_id="elena-sse-2")
    )
    e2 = harness.event_feed.record_event(
        PlanningCompleted(run_id="run-sse-2", spec_id="spec-1")
    )
    e3 = harness.event_feed.record_event(
        PrototypeReady(run_id="run-sse-2", prototype_ref="preview-rev0")
    )

    # Reconnect asking for events after e1
    async with AsyncClient(
        transport=ASGITransport(app=harness.app),
        base_url="http://testserver",
        headers={"X-API-Key": TEST_API_KEY, "Last-Event-ID": e1.event_id},
    ) as ac:
        async with ac.stream("GET", "/api/v1/runs/run-sse-2/events") as response:
            assert response.status_code == 200
            lines = []
            saw_e3 = False
            async for line in response.aiter_lines():
                lines.append(line)
                if f"id: {e3.event_id}" in line:
                    saw_e3 = True
                if saw_e3 and line == "":
                    break

            combined = "\n".join(lines)
            # e1 should NOT be replayed because we asked for events strictly after e1
            assert f"id: {e1.event_id}" not in combined
            assert f"id: {e2.event_id}" in combined
            assert f"id: {e3.event_id}" in combined
            assert "event: PlanningCompleted" in combined
            assert "event: PrototypeReady" in combined


@pytest.mark.anyio
async def test_stream_events_run_isolation(harness: APITestHarness) -> None:
    """Client streaming run A does not receive events belonging to run B."""
    brief = make_sample_brief()
    run_a = Run(run_id="run-iso-A", project_id="elena-A", brief=brief)
    run_b = Run(run_id="run-iso-B", project_id="elena-B", brief=brief)
    harness.repository.save(run_a)
    harness.repository.save(run_b)

    # Record events for run B
    ev_b = RunStarted(run_id="run-iso-B", project_id="elena-B")
    harness.event_feed.record_event(ev_b)

    # Connect to run A
    async with AsyncClient(
        transport=ASGITransport(app=harness.app),
        base_url="http://testserver",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        async with ac.stream("GET", "/api/v1/runs/run-iso-A/events") as response:
            assert response.status_code == 200
            # Read keep-alive or empty stream
            chunk = await anext(response.aiter_text())
            assert "run-iso-B" not in chunk


@pytest.mark.anyio
async def test_stream_events_non_existent_run_returns_404(
    harness: APITestHarness,
) -> None:
    """Connecting to a stream for an unknown run ID returns 404."""
    async with AsyncClient(
        transport=ASGITransport(app=harness.app),
        base_url="http://testserver",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        res = await ac.get("/api/v1/runs/non-existent-run-xyz/events")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "RUN_NOT_FOUND"
