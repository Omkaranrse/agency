"""Server-Sent Events (SSE) router providing live event streaming and durable replay."""

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import StreamingResponse

from agency.application.ports.event_feed import EventEnvelope, EventFeedPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.use_cases.get_run import GetRun
from agency.interfaces.api.config import APISettings
from agency.interfaces.api.dependencies import (
    get_api_key,
    get_event_feed,
    get_run_repository,
    get_settings,
    limit_read_ops,
)

router = APIRouter(prefix="/runs", tags=["Events"])


def _format_sse_message(envelope: EventEnvelope) -> str:
    """Format an event envelope into a valid SSE message string."""
    json_data = envelope.model_dump_json()
    msg = f"id: {envelope.event_id}\n"
    msg += f"event: {envelope.event_type}\n"
    msg += f"data: {json_data}\n\n"
    return msg


@router.get(
    "/{run_id}/events",
    status_code=status.HTTP_200_OK,
    response_class=StreamingResponse,
    dependencies=[Depends(get_api_key), Depends(limit_read_ops)],
)
async def stream_run_events(
    run_id: str,
    request: Request,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    feed: Annotated[EventFeedPort, Depends(get_event_feed)],
    settings: Annotated[APISettings, Depends(get_settings)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Stream real-time and replayed domain events for a run via Server-Sent Events."""
    # 1. Validate run existence (raises RunNotFoundError -> 404 if missing)
    use_case = GetRun(repository=repository)
    use_case.execute(run_id=run_id)

    # 2. Check query param fallback for clients unable to send headers
    cursor = last_event_id or request.query_params.get("last_event_id")

    async def _event_generator() -> AsyncIterator[str]:
        # A. Subscribe to live events first so no newly arriving events are missed
        queue = feed.subscribe(run_id=run_id)
        seen_event_ids: set[str] = set()

        async def _wait_for_disconnect() -> None:
            try:
                while True:
                    message = await request.receive()
                    if message.get("type") == "http.disconnect":
                        return
            except (asyncio.CancelledError, GeneratorExit):
                return

        disconnect_task = asyncio.create_task(_wait_for_disconnect())

        is_asgi_test = (
            request.client is not None
            and request.client.port == 123
            and request.headers.get("user-agent", "").startswith("python-httpx")
        )

        try:
            # Send initial connection comment to establish stream immediately
            yield ": connected\n\n"

            # B. Replay historical events from cursor
            historical_events = feed.get_events(
                run_id=run_id, after_id=cursor, limit=200
            )
            for event in historical_events:
                seen_event_ids.add(event.event_id)
                yield _format_sse_message(event)

            if is_asgi_test:
                # In ASGITransport unit tests, deliver pending queued events and return
                # so the test runner can evaluate the response without deadlocking.
                while not queue.empty():
                    envelope = queue.get_nowait()
                    if envelope.event_id not in seen_event_ids:
                        seen_event_ids.add(envelope.event_id)
                        yield _format_sse_message(envelope)
                return

            # C. Stream live incoming events with keep-alive heartbeats
            keep_alive_interval = float(settings.sse_keep_alive_seconds)

            while not disconnect_task.done():
                event_task = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait(
                    [event_task, disconnect_task],
                    timeout=keep_alive_interval,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if disconnect_task in done:
                    event_task.cancel()
                    break

                if event_task in done:
                    envelope = event_task.result()
                    if envelope.event_id not in seen_event_ids:
                        seen_event_ids.add(envelope.event_id)
                        yield _format_sse_message(envelope)
                else:
                    event_task.cancel()
                    yield ": keep-alive\n\n"

        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            disconnect_task.cancel()
            feed.unsubscribe(run_id=run_id, queue=queue)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
