'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '@/lib/api/config';
import type { DomainEventEnvelope, EventStreamStatus } from './types';

export interface UseRunEventStreamOptions {
  runId: string | undefined;
  enabled?: boolean;
  onEvent?: (event: DomainEventEnvelope) => void;
  onStatusChange?: (status: EventStreamStatus) => void;
}

export interface UseRunEventStreamReturn {
  events: DomainEventEnvelope[];
  status: EventStreamStatus;
  error: string | null;
  reconnect: () => void;
  clearEvents: () => void;
}

const MIN_RETRY_DELAY = 1000;
const MAX_RETRY_DELAY = 30000;
const RETRY_BACKOFF_FACTOR = 1.5;

export function useRunEventStream({
  runId,
  enabled = true,
  onEvent,
  onStatusChange,
}: UseRunEventStreamOptions): UseRunEventStreamReturn {
  const [events, setEvents] = useState<DomainEventEnvelope[]>([]);
  const [status, setStatus] = useState<EventStreamStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);

  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const lastEventIdRef = useRef<string | null>(null);
  const retryCountRef = useRef<number>(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isUnmountedRef = useRef<boolean>(false);

  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const onStatusChangeRef = useRef(onStatusChange);
  onStatusChangeRef.current = onStatusChange;

  const updateStatus = useCallback((newStatus: EventStreamStatus) => {
    setStatus(newStatus);
    onStatusChangeRef.current?.(newStatus);
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
    seenEventIdsRef.current.clear();
    lastEventIdRef.current = null;
  }, []);

  const connect = useCallback(() => {
    if (!runId || !enabled || isUnmountedRef.current) return;

    // Clean up any ongoing fetch
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const isReconnecting = retryCountRef.current > 0;
    updateStatus(isReconnecting ? 'reconnecting' : 'connecting');
    setError(null);

    // Build URL with query parameter for cursor resume
    const cursor = lastEventIdRef.current;
    const url = new URL(`${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId)}/events`);
    if (cursor) {
      url.searchParams.set('last_event_id', cursor);
    }

    const headers: Record<string, string> = {
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    };

    if (cursor) {
      headers['Last-Event-ID'] = cursor;
    }

    try {
      const apiKey = localStorage.getItem('agency-api-key');
      if (apiKey) {
        headers['X-API-Key'] = apiKey;
      }
    } catch {
      // localStorage may fail
    }

    fetch(url.toString(), {
      method: 'GET',
      headers,
      signal: abortController.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          // Terminal errors: 401, 403, 404 should not enter infinite reconnect loop
          if (response.status === 401 || response.status === 403) {
            updateStatus('error');
            setError('Authentication failed. Stream connection denied.');
            return;
          }
          if (response.status === 404) {
            updateStatus('error');
            setError('Run not found. Event streaming unavailable.');
            return;
          }

          throw new Error(`SSE stream returned status ${response.status}`);
        }

        if (!response.body) {
          throw new Error('SSE response body is empty');
        }

        // Connection established successfully
        retryCountRef.current = 0;
        updateStatus('connected');
        setError(null);

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        let currentEventId: string | null = null;
        let currentEventType: string | null = null;
        let currentEventData = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          // Keep the last partial line in buffer
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            const trimmed = line.trim();

            if (!trimmed) {
              // Empty line marks end of an event block
              if (currentEventData) {
                try {
                  const payload = JSON.parse(currentEventData);
                  const envelope: DomainEventEnvelope = {
                    event_id: currentEventId || payload.event_id || `evt-${Date.now()}-${Math.random()}`,
                    run_id: payload.run_id || runId,
                    event_type: currentEventType || payload.event_type || 'Event',
                    occurred_at: payload.occurred_at || new Date().toISOString(),
                    payload: payload.payload || payload,
                  };

                  if (!seenEventIdsRef.current.has(envelope.event_id)) {
                    seenEventIdsRef.current.add(envelope.event_id);
                    lastEventIdRef.current = envelope.event_id;

                    setEvents((prev) => [...prev, envelope]);
                    onEventRef.current?.(envelope);
                  }
                } catch {
                  // Ignore JSON parse failure for malformed data
                }
              }

              // Reset per-event fields
              currentEventId = null;
              currentEventType = null;
              currentEventData = '';
              continue;
            }

            if (trimmed.startsWith(':')) {
              // Comment / keep-alive heartbeat
              continue;
            }

            if (trimmed.startsWith('id:')) {
              currentEventId = trimmed.slice(3).trim();
            } else if (trimmed.startsWith('event:')) {
              currentEventType = trimmed.slice(6).trim();
            } else if (trimmed.startsWith('data:')) {
              const dataContent = trimmed.slice(5).trim();
              currentEventData += dataContent;
            }
          }
        }

        // Stream completed normally or server closed
        if (!isUnmountedRef.current && enabled) {
          scheduleReconnectRef.current();
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;

        if (!isUnmountedRef.current && enabled) {
          scheduleReconnectRef.current();
        }
      });
  }, [runId, enabled, updateStatus]);

  const scheduleReconnectRef = useRef<() => void>(() => {});

  const scheduleReconnect = useCallback(() => {
    retryCountRef.current += 1;
    updateStatus('reconnecting');

    // Bounded exponential backoff with jitter
    const delay = Math.min(
      MIN_RETRY_DELAY * Math.pow(RETRY_BACKOFF_FACTOR, retryCountRef.current) +
        Math.random() * 1000,
      MAX_RETRY_DELAY
    );

    setError(`Disconnected from event feed. Reconnecting in ${Math.round(delay / 1000)}s...`);

    retryTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect, updateStatus]);

  scheduleReconnectRef.current = scheduleReconnect;

  useEffect(() => {
    isUnmountedRef.current = false;

    if (enabled && runId) {
      connect();
    } else {
      updateStatus('disconnected');
    }

    return () => {
      isUnmountedRef.current = true;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
    };
  }, [runId, enabled, connect, updateStatus]);

  const manualReconnect = useCallback(() => {
    retryCountRef.current = 0;
    connect();
  }, [connect]);

  return {
    events,
    status,
    error,
    reconnect: manualReconnect,
    clearEvents,
  };
}
