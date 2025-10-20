"""Web-facing observers for pantry events.

This module subscribes to the GLOBAL_EVENT_BUS for:
  - pantry.low_stock
  - pantry.near_expiry

and stores a lightweight in-memory ring buffer of recent events that can be
queried by the web layer (FastAPI endpoint) to show real-time style alerts
on the pages without a full page reload.

Design:
  * Each event stored with an auto-increment integer id (cursor) so clients
    can request only newer events (since=<last_id_seen>). This keeps payloads
    small and polling efficient.
  * Thread-safety ensured with a simple Lock (FastAPI + uvicorn workers may
    share process; for multi-process deployment this remains per-process which
    is fine for non-critical notifications).
  * A MAX_EVENTS cap prevents unbounded memory growth.
"""
from __future__ import annotations
from typing import List, Dict, Any
from threading import Lock
from datetime import datetime

from .Event_Bus import (
    GLOBAL_EVENT_BUS, PANTRY_LOW_STOCK, PANTRY_NEAR_EXPIRY
)

_lock = Lock()
_events: List[Dict[str, Any]] = []
_next_id = 1
MAX_EVENTS = 300  # keep a few hundred recent events
_started = False


def _record(event_name: str, payload: Any):  # signature expected by EventBus
    global _next_id
    try:
        with _lock:
            evt = {
                'id': _next_id,
                'type': event_name,
                'ts': datetime.utcnow().isoformat() + 'Z'
            }
            # Normalize payload fields we care about for UI
            if isinstance(payload, dict):
                ing = payload.get('ingredient')
                if ing and hasattr(ing, 'name'):
                    evt['name'] = getattr(ing, 'name', '')
                    evt['unit'] = getattr(ing, 'unit', '')
                    evt['quantity'] = getattr(ing, 'default_quantity', '')
                # Copy common numeric fields
                for k in ('remaining', 'threshold', 'days_left'):
                    if k in payload:
                        evt[k] = payload[k]
                # Fallback direct fields if ingredient was just a dict
                if 'ingredient' in payload and isinstance(payload['ingredient'], dict):
                    for k in ('name','unit','default_quantity'):
                        if k in payload['ingredient'] and k not in evt:
                            evt[k] = payload['ingredient'][k]
            _events.append(evt)
            _next_id += 1
            # Trim buffer
            if len(_events) > MAX_EVENTS:
                del _events[: len(_events) - MAX_EVENTS]
    except Exception as e:  # pragma: no cover - defensive
        print(f"[web_observers] Failed to record event {event_name}: {e}")


def start():
    """Idempotent start: subscribe observers once."""
    global _started
    if _started:
        return
    GLOBAL_EVENT_BUS.subscribe(PANTRY_LOW_STOCK, _record)
    GLOBAL_EVENT_BUS.subscribe(PANTRY_NEAR_EXPIRY, _record)
    _started = True


def get_events(since: int | None = None) -> Dict[str, Any]:
    """Return events newer than 'since' (exclusive).

    If since is None, returns the last N (up to MAX_EVENTS) events.
    Response includes next_cursor (largest id) so client can poll with since=next_cursor.
    """
    with _lock:
        if since is None:
            data = list(_events)
        else:
            data = [e for e in _events if e['id'] > since]
        next_cursor = _events[-1]['id'] if _events else since or 0
    return {'events': data, 'next_cursor': next_cursor}


__all__ = ['start', 'get_events']
