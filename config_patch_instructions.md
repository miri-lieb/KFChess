# One small code change required before the containers will work

`config.py` currently hardcodes these values:

```python
NETWORK_HOST = "127.0.0.1"
NETWORK_PORT = 8765
DB_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "kfchess.db")
```

`127.0.0.1` will NOT accept connections from outside the container, and the DB path needs
to point at the mounted volume (`/data/kfchess.db`) so data survives container restarts.

Replace those three lines in `config.py` with:

```python
NETWORK_HOST = _os.environ.get("NETWORK_HOST", "127.0.0.1")
NETWORK_PORT = int(_os.environ.get("NETWORK_PORT", "8765"))
DB_PATH = _os.environ.get(
    "DB_PATH",
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "kfchess.db"),
)
```

This keeps local (non-Docker) behavior identical (same defaults), while letting
`docker-compose.yml`'s `environment:` block override them inside the container.

No other code changes are required to get the base server running in Docker Compose.
Redis / Postgres / NATS containers are included and reachable, but the code does not
use them yet — that's the next step (room_id tagging + Redis-backed room registry),
not part of "get it running in containers."
