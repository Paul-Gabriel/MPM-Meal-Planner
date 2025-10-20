"""Simple Event Bus / Observer implementation for pantry alerts.

Event names used so far:
  pantry.low_stock -> payload {"ingredient": Ingredient, "remaining": int, "threshold": int}
  pantry.near_expiry -> payload {"ingredient": Ingredient, "days_left": int, "threshold": int}

Subscribers can be callables or objects exposing handle_event(event_name, payload).
"""
from __future__ import annotations
from collections import defaultdict
from typing import Callable, Any, Dict, List

# --- Event name constants (used across modules) ---
PANTRY_LOW_STOCK = "pantry.low_stock"
PANTRY_NEAR_EXPIRY = "pantry.near_expiry"
PANTRY_EXPIRING_SNAPSHOT = "pantry.expiring_snapshot"


class EventBus:
	def __init__(self):
		self._subscribers: Dict[str, List[Callable[[str, Any], None]]] = defaultdict(list)

	def subscribe(self, event_name: str, callback: Callable[[str, Any], None]):
		if callback not in self._subscribers[event_name]:
			self._subscribers[event_name].append(callback)

	def unsubscribe(self, event_name: str, callback: Callable[[str, Any], None]):
		try:
			self._subscribers[event_name].remove(callback)
		except (ValueError, KeyError):
			pass

	def publish(self, event_name: str, payload: Any):
		for cb in list(self._subscribers.get(event_name, [])):
			try:
				cb(event_name, payload)
			except Exception as e:  # pragma: no cover - defensive
				print(f"[EventBus] Error delivering {event_name} to {cb}: {e}")


# A singleton-like instance (can be imported)
GLOBAL_EVENT_BUS = EventBus()


def simple_print_listener(event_name: str, payload: Any):  # Example listener
	print(f"[EVENT] {event_name}: {payload}")


# Helper scurt pentru publicare evenimente din alte module
def crea(event_name: str, payload: Any = None) -> None:
	"""Publish an event on the global bus (sugar function)."""
	GLOBAL_EVENT_BUS.publish(event_name, payload)


# Alias semantic
create_event = crea

__all__ = [
	'EventBus', 'GLOBAL_EVENT_BUS', 'crea', 'create_event', 'simple_print_listener',
	'PANTRY_LOW_STOCK', 'PANTRY_NEAR_EXPIRY', 'PANTRY_EXPIRING_SNAPSHOT'
]
