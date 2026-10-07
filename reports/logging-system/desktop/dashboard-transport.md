# 🖥️ Desktop: Dashboard Transport — SocketManager + DesktopDashboardManager

## Domain & Dependencies

**Domain:** `desktop` — this document covers how logs physically travel from the main
app process to the dashboard process: TCP sockets, subprocess spawning, terminal
emulator selection.

**Dependencies:**
- **Core Logging System** (`../core/handler-architecture.md`): the `LogEntry` protocol
  being shipped, the `DashboardManager` abstract contract it implements.
- **Desktop Handler** (`dashboard-handler.md`): `DashBoardHandler` — the caller that
  drives this transport.
- **Dashboard Printer** (`dashboard-printer.md`): the receiving end (`runner_server.py`).

---

## 1. Executive Summary

The transport is a **one-way TCP pipe** from the main app process (client) to a
dashboard process (server). The desktop *manager* (`DesktopDashboardManager`) spawns
the server in its own terminal window, then the *client socket singleton*
(`ClientSocketManager`) connects and ships JSON-serialized `LogEntry` records.
Health is verified before every send with a `SO_ERROR` + `MSG_PEEK` probe so a dead
server never hangs the app.

**Metaphor:** a conveyor belt to a sister plant. Before pushing a package (a log) onto
the belt, an inspector taps a tester button (`is_connected_status()`) — if the belt is
jammed, the package is set aside instead of causing a pile-up.

---

## 2. The Wire — What Actually Travels

`DesktopDashboardManager.send_to_dashboard()`:

```python
payload_log_entry = asdict(log_entry)     # dataclass → dict
data = json.dumps(asdict(log_entry), indent=2).encode()
client_manager.send_message(data)          # sendall() over the socket
```

- Format: **pretty-printed JSON** of the `LogEntry` fields
  (`LOG_TYPE`, `LOG_LEVEL`, `MESSAGE`, `TIME_STAMP`, `METADATA`).
- Direction: client → server only. The server is a receiver, never a sender —
  this is why the client's health probe below treats *any* incoming byte as "FIN = dead."

⚠️ Enum risk: `LogCategory`/`LogLevel` are enums — `json.dumps` can't serialize them.
The memory log (2026-08-14) records the fix (value extraction during `asdict` or a
custom default), and `Dispatcher._convert_str_log_entry` on the receiving parse path
accepts both enum *names* and raw values.

---

## 3. The Four Players (all in `desktop/dashboard/dashboard_transport.py`)

### 3.1 `SocketManager.ServerConfig` — shared constants

```python
@dataclass(frozen=True)
class ServerConfig:
    SERVER_PORT: int = 59700
    SERVER_HOST: str = "127.0.0.1"
    LISTNERS: int = 1          # max queued connects
    BAND_WIDTH: int = 1024 * 1024   # recv buffer: 1 MiB
```

Both ends (client & server) read this same frozen config → can't drift.

### 3.2 `ServerSocketManager` — lives inside the dashboard process

```python
def start_server(self):
    socket(AF_INET, SOCK_STREAM)
    → SO_REUSEADDR / SO_KEEPALIVE / TCP_NODELAY
    → bind((127.0.0.1, 59700)); listen(1)
    → accept()  # exactly one client, blocks until the app connects
```

`recieve_raw_log(queue_ptr)` then loops `recv(1 MiB)` and appends decoded strings to
the caller's `deque`. Fixes on record (memory 2026-09-14):

- `settimeout(None)` after `accept()` — prevents idle-socket timeouts.
- Socket teardown moved *outside* the receive loop — fixes `OSError [Errno 9]`.
- Newline stream buffering — JSON messages are framed on newlines, preventing
  partial-JSON decode errors when a `recv()` call splits a message.

### 3.3 `ClientSocketManager` — lives inside the main app

```python
connect_to_server()   # TCP connect to 127.0.0.1:59700 or raise
send_message(bytes)   # sendall; BrokenPipe/ConnectionReset → connection_alive=False, raise
is_connected_status() # the health probe — see §4
```

### 3.4 `DesktopDashboardManager` — the process orchestrator

Implements core's abstract `DashboardManager`:

- **`start_dashboard()`** — picks the first available terminal from an ordered list
  (`qterminal` → `gnome-terminal` → `xterm` → `konsole` → `tmux`; the kitty-first
  variant with `--hold` and `start_new_session=True` was applied on 2026-09-14) and
  `Popen`s:
  ```
  bash -c "cd '<cwd>' && uv run python '<repo>/desktop/.../runner_server.py>; echo …; read"
  ```
  The `bash -c` + read/hold wrapper keeps the window open after the server exits for
  forensic reading. On Windows the equivalent is `CREATE_NEW_CONSOLE`.
- **`send_to_dashboard(log_entry)`** — gates on `server_process.poll() is None`
  (subprocess alive) + `is_connected_status()` (TCP healthy), then ships JSON.

---

## 4. The Health Probe — `is_connected_status()` Explained

Plain sockets give you almost no "dead?" signal until a send *actually fails*. The
client does better with two cheap syscalls:

1. **`getsockopt(SO_ERROR)`** — non-zero → error flag set (e.g. RST from a crashed server).
2. **`select([sock], [], [], 0)`** — "does the kernel have pending data?" If yes, peek one
   byte with `recv(1, MSG_PEEK)`:
   - `len > 0` → unexpected inbound data → treated as anomalous.
   - `len == 0` → the kernel received **FIN** (server closed gracefully) → dead.
   - No data at all → connection is alive and quiet → healthy.

This pairs perfectly with the protocol's direction (client→server only): any inbound
byte is a red flag by construction.

---

## 5. Cold-Start Sequence (where the 3 s pause lives)

```mermaid
sequenceDiagram
  participant H as DashBoardHandler
  participant M as DesktopDashboardManager
  participant C as ClientSocketManager
  participant T as Terminal Emulator
  participant S as ServerSocketManager

  H->>M: start_dashboard()
  M->>T: Popen(bash -c '… uv run python runner_server.py')
  T->>S: python import → bind 59700 → listen → accept() [blocks]
  Note over H: sleep(3) — hardcoded cold-start budget
  H->>C: connect_to_server()
  C-->>S: TCP handshake
  S-->>C: accept() returns; settimeout(None)
  H->>C: sendall(json(LogEntry)) × each subsequent log
```

The 3 s `sleep` in `DashBoardHandler.handle()` (not here) is what compensates for the
`uv run + interpreter + bind` latency. Long-term fix per in-code TODO: a lock file +
readiness probe instead of a fixed sleep.

---

## 6. Known Sharp Edges

- **Spawn race** — `start_dashboard()` checks `server_process.poll() is None`, but between
  the check and the terminal actually starting the server (1–2 s), a second call can pass
  the same check → duplicate windows. Lock-file approach TODO'ed.
- **Terminal matrix** — nothing checks the dashboards' rendering target; each terminal
  emulator handles ANSI/Rich differently.
- **No auto-heal** — if `is_connected_status()` fails mid-session, the code reports it
  ("server process is alive but connection is dead") and drops the log rather than
  reconnecting.
- **Port is hardcoded** (`59700`) — a second app instance collides; `SO_REUSEADDR` only
  softens rebinding of a *closed* socket.

---

## 7. Quick Reference

| You want… | Where |
|---|---|
| Change the port/host | `SocketManager.ServerConfig` (SERVER_PORT / SERVER_HOST) |
| Understand "did the server die?" | `ClientSocketManager.is_connected_status()` |
| Terminal fallback order | `DesktopDashboardManager.start_dashboard()` `terminals` list |
| Server loop internals | `ServerSocketManager.recieve_raw_log()` |
| Sends/hangs in send path | called thread; `sendall` blocks until kernel accepts |

---

## 8. Q&A Log

> Q: Why TCP over localhost instead of a Unix domain socket?
> Portability — the same code runs on Windows (`CREATE_NEW_CONSOLE` path) where Unix
> sockets historically weren't available (added in Windows 10 1809+). TCP works everywhere.

> Q: Why one single client?
> The dashboard server is one Rich console — multiplexing producers would garble its
> output. `LISTNERS = 1` makes that an OS-level rule, not a convention.

> Q: What happens if a log is > 1 MiB?
> `BAND_WIDTH` governs a single `recv()` call; newline-delimited framing means big
> messages simply span multiple `recv()` iterations and are reassembled in the queue.