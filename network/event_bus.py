from dataclasses import dataclass
from typing import Any, Callable, Optional

@dataclass(frozen=True)
class GameEvent:
    # A single event that flows between publishers and subscribers.
    type: str
    payload: dict[str, Any]

# Function type for an event handler.
EventHandler = Callable[[GameEvent], None]

class InMemoryEventBus:
    # Simple in-memory bus: keeps global subscribers and event-specific subscribers.
    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._global_subscribers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler, event_type: Optional[str] = None) -> None:
        if event_type is None:
            # A global subscriber receives every published event.
            self._global_subscribers.append(handler)
            return
        # A targeted subscriber receives only the requested event type.
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload: dict[str, Any]) -> GameEvent:
        # Create the event and dispatch it to global subscribers first, then specific ones.
        event = GameEvent(type=event_type, payload=payload)
        for handler in self._global_subscribers:
            handler(event)
        for handler in self._subscribers.get(event_type, []):
            handler(event)
        return event