import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


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


class NATSEventBus:
    def __init__(self, nats_url: str, room_id: str):
        self._nats = None
        self._nats_url = nats_url
        self._room_id = room_id
        self._connected = False
        self._local = InMemoryEventBus()
        self._nats_subscriptions: list = []

    async def connect(self) -> None:
        try:
            import nats as nats_mod

            self._nats = await nats_mod.connect(self._nats_url)
            self._connected = True
            logger.info("NATS connected for room %s", self._room_id)
        except Exception as exc:
            logger.warning(
                "NATS unavailable for room %s, using in-memory fallback: %s",
                self._room_id,
                exc,
            )
            self._nats = None
            self._connected = False

    async def close(self) -> None:
        for sub in self._nats_subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        self._nats_subscriptions.clear()
        if self._nats is not None:
            try:
                await self._nats.drain()
            except Exception:
                pass
            self._nats = None
            self._connected = False

    def subscribe(self, handler: EventHandler, event_type: Optional[str] = None) -> None:
        self._local.subscribe(handler, event_type)

    async def subscribe_nats(self, handler: Callable[[str, dict], None], event_type: Optional[str] = None) -> None:
        if not self._connected or self._nats is None:
            return
        if event_type is not None:
            subject = f"game.room.{self._room_id}.{event_type}"
        else:
            subject = f"game.room.{self._room_id}.>"

        async def _msg_handler(msg):
            try:
                payload = json.loads(msg.data.decode())
                event_type_part = msg.subject.split(".")[-1]
                handler(event_type_part, payload)
            except Exception as exc:
                logger.warning("NATS message handler error: %s", exc)

        sub = await self._nats.subscribe(subject, cb=_msg_handler)
        self._nats_subscriptions.append(sub)

    def publish(self, event_type: str, payload: dict[str, Any]) -> GameEvent:
        event = GameEvent(type=event_type, payload=payload)

        if self._connected and self._nats is not None:
            subject = f"game.room.{self._room_id}.{event_type}"

            async def _publish():
                try:
                    await self._nats.publish(subject, json.dumps(payload).encode())
                except Exception as exc:
                    logger.warning("NATS publish failed for room %s: %s", self._room_id, exc)

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_publish())

        for handler in self._local._global_subscribers:
            handler(event)
        for handler in self._local._subscribers.get(event_type, []):
            handler(event)
        return event

    @property
    def is_connected(self) -> bool:
        return self._connected
