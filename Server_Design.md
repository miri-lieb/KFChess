# Server Design — Scalable Multiplayer Game Server

## 1. Overview

This document describes the design for scaling our game server to support:
- 100,000,000 registered users
- 10,000,000 concurrent active players worldwide
- Real-time gameplay with ~1 move every 2 seconds per active player
- Short game sessions (30–90 seconds each)

The design follows the architecture direction shared by the reviewers (API Gateway / WS Gateway / Matchmaker / Game Allocator / Game Server Shards / NATS event bus / Redis / PostgreSQL / Kubernetes-K3s), adapted to our own game engine and current implementation.

Core principle carried over from our current codebase: **the client never decides game rules, and neither does any gateway. The `GameEngine` running inside a Game Server Shard is the single source of truth for game state.**

---

## 2. Components

| Component | Responsibility |
|---|---|
| **API Gateway** | Non-real-time HTTP/REST: login, room creation/listing, match history. |
| **WS Gateway** | Live WebSocket connections with clients. Async I/O, no thread-per-client. Forwards player commands to the correct room via the event bus, and pushes state updates back to clients. |
| **Matchmaker** | Pairs/groups players into a match based on queue rules. |
| **Game Allocator** | Decides which Game Server Shard will host a given room, and records the mapping. |
| **Game Server Shards** | Each shard runs many rooms concurrently, each with its own authoritative `GameEngine` instance and a per-room command queue. |
| **NATS Event Bus** | Internal pub/sub between services. Events are published/subscribed **per room** (e.g. subject `game.room.<room_id>.*`), so a shard only receives events for rooms it actually owns. This directly fixes the cross-room event-leak bug we found in the current implementation (a single shared global event bus + global broadcast with no `room_id` tagging). |
| **Redis** | Fast, ephemeral state: sessions, active room registry (`room_id → shard_id`), reconnect tokens, matchmaking queue. |
| **PostgreSQL** | Durable data: users, completed games, results, move history (written asynchronously/batched, not per-move). |
| **Observability** | Logs, metrics, health checks, alerting, load testing. |
| **Kubernetes / K3s (+ optional Agones)** | Container orchestration, autoscaling of shards, fleet management. |

---

## 3. Answers to the design questions

### 3.1 — 100M registered users: is SQLite suitable?

**No.** SQLite is a single-writer, single-file, single-machine database. It has no built-in replication, no concurrent multi-writer support across a network, and no horizontal scalability. For 100M users we need a real relational database — **PostgreSQL** — with:
- Connection pooling (e.g. PgBouncer) to handle many shard/service connections.
- Proper indexing on user/game lookups.
- Read replicas for read-heavy queries (history, profiles).
- Future option (if needed beyond this scale): sharding via Citus, or a distributed SQL database (e.g. CockroachDB). Not required at our current target, but worth knowing as the next step.

### 3.2 — 10M concurrent players: is one server enough?

**No — sharding by room is required.**

- When a room is created, the **Game Allocator** picks a shard (e.g. round-robin or least-loaded) and stores the mapping `room_id → shard_id` in Redis.
- A player's WebSocket connection can land on **any** WS Gateway instance (behind a load balancer) — the gateway doesn't need to physically host the room. Instead, the gateway forwards the player's command over NATS to a subject scoped to that room (`game.room.<room_id>.move`), and only the shard that owns that room is subscribed to it.
- This is exactly how "everyone can play with everyone, and join any room" — routing happens at the event-bus layer (by room_id), not at the TCP-connection layer.
- Each shard owns a subset of rooms; shards are added/removed elastically as load changes.

### 3.3 — Network traffic: one move every 2 seconds per active player

Rough estimate:
- 10,000,000 players / 2 seconds ≈ **5,000,000 incoming messages/second**.
- Even at a small message size (~200–300 bytes JSON), that's roughly **1.2–1.5 GB/s inbound ≈ 10–12 Gbps**.
- Add outbound broadcast to opponents/observers (roughly doubling), and total traffic is in the range of **20–40 Gbps** and several million messages/second.

This is a **large** amount of traffic — well beyond what a single machine (or even a single NIC) can efficiently handle, both due to raw bandwidth and per-message overhead. This is the core reason the architecture must scale **horizontally** across many shards/machines rather than relying on a single stronger server.

### 3.4 — Games last 30–90 seconds: implications for shard/container roles

- Very short game lifetimes mean **many rooms are created and destroyed every second**. Spinning up a dedicated container per room would be far too slow and wasteful (container start/teardown overhead vs. a 30–90 second game).
- Instead, each **Game Server Shard is a long-running process managing thousands of lightweight rooms in memory concurrently**, each with its own command queue — not one container per game.
- The **Game Allocator must be very fast** (sub-second) since allocation overhead is a meaningful fraction of a 30–90 second game if it's slow.
- Writes to PostgreSQL (move history, results) **cannot be synchronous per move** — they must be buffered/batched (e.g. written to Redis first, then flushed to Postgres asynchronously), or the DB will not keep up with the write rate.
- Autoscaling (K3s / Agones) needs to be elastic and fast-reacting, since load shifts throughout the day across world time zones.

---

## 4. What this fixes from our current implementation

Our current implementation had a single global event bus shared across all rooms, with broadcasts sent to *all* connected clients regardless of room, and no `room_id` field in event payloads — causing moves in one room to visibly affect another room's board. The design above solves this at scale by:
- Tagging every event with `room_id`.
- Scoping the NATS subject/subscription per room, so a shard (and its connected clients) only ever receives events for rooms it owns.
- Never relying on a single shared in-process event bus across independent games.

---

## 5. Rollout plan

1. Implement a small, working version locally with **Docker Compose**: API Gateway, WS Gateway, one Game Server Shard, Redis, Postgres, NATS.
2. Verify room isolation end-to-end (two rooms open at once, no cross-talk).
3. Add Matchmaker + Game Allocator once single-shard flow works correctly.
4. Only after that: move to Kubernetes/K3s for multi-shard orchestration and autoscaling.
5. Add observability (logs/metrics/health checks) alongside each step, not as an afterthought.

**Priority: a small working system beats a large, ambitious, non-working one.**
