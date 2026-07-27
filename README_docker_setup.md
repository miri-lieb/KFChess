# Running KFChess server with Docker Compose

## Files to drop into the repo root
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- Apply the one small change in `config_patch_instructions.md` to `config.py`

## Run it

```bash
docker compose up --build
```

This starts:
- `server` — your existing WebSocket game server, now listening on `ws://localhost:8765` from outside the container.
- `redis` — empty for now, reachable at `localhost:6379`.
- `postgres` — empty for now, reachable at `localhost:5432` (user/pass/db: `kfchess`/`kfchess`/`kfchess`).
- `nats` — empty for now, reachable at `localhost:4222` (monitoring UI at `localhost:8222`).

## Verify it works

From the host machine (outside any container), run your existing shell client against it,
e.g.:

```bash
python -m network.shell_client --host localhost --port 8765
```

Open two rooms as described earlier and confirm moves in one room do not affect the other
(this was the bug we found — it is not yet fixed by this step, only containerized).

## What this step does NOT do yet

- Does not fix the cross-room event leak (still the same single global `InMemoryEventBus`,
  just now running inside a container instead of on bare metal).
- Does not use Redis, Postgres, or NATS from the code — they are just running and reachable,
  ready for the next iteration.
- Does not add Matchmaker / Game Allocator / multiple shards.

## Suggested next commits, in order

1. Apply the room_id-tagging fix (see the earlier bug-fix prompt) so a single shard can
   safely host many isolated rooms.
2. Wire Redis in for the active-room registry (`room_id -> shard_id`) even with only one
   shard — this gets the interface right before scaling out.
3. Only once (1) and (2) work and are tested: consider adding a second shard + NATS-based
   routing between shards.

Keep committing small, working states — this setup is intentionally the smallest slice
that gets you "containerized and reachable" without touching game logic.
