from dataclasses import dataclass
from typing import Any, Callable, Optional

@dataclass(frozen=True)
class GameEvent:
    type: str
    payload: dict[str, Any]

EventHandler = Callable[[GameEvent], None]

class InMemoryEventBus:
    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._global_subscribers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler, event_type: Optional[str] = None) -> None:
        if event_type is None:
            self._global_subscribers.append(handler)
            return
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload: dict[str, Any]) -> GameEvent:
        event = GameEvent(type=event_type, payload=payload)
        for handler in self._global_subscribers:
            handler(event)
        for handler in self._subscribers.get(event_type, []):
            handler(event)
        return event