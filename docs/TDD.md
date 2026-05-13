# Charm Studio — Agent Service Technical Design Document

## Overview

The **studio_agent** service is a lightweight HTTP API that orchestrates the
full repo-to-deployment pipeline for charm applications. It runs three
sequential stages — **analyze**, **pack**, and **deploy** — as a single
asynchronous pipeline task, reporting stage-by-stage progress back to the
caller (a Svelte frontend).

The service is shipped as a **classic snap**. All state is self-contained — no
external services (databases, message brokers) are required.

---

## The Full Pipeline

```
Svelte frontend
     │
     ▼
POST /pipeline  { project_id }
     │
     ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │ Huey worker                                                     │
 │                                                                 │
 │  [analyze]  opencode run <instruction>                          │
 │      │      verifies repo is a valid charm repo                 │
 │      ▼                                                          │
 │  [pack]     charmcraft pack                                     │
 │      │      rockcraft pack                                      │
 │      ▼                                                          │
 │  [deploy]   juju add-model <uuid>                               │
 │             juju deploy ./<charm-file> <uuid>                   │
 │                  --resource <image> -m <uuid>                   │
 │             juju integrate <uuid> <haproxy-offer>               │
 └─────────────────────────────────────────────────────────────────┘
     │
     ▼
GET /status/<pipeline_id>
```

---

## API

### `POST /pipeline`

Enqueues a full analyze → pack → deploy pipeline for the specified project.

**Request body** (JSON):

```json
{ "project_id": "<project-id>" }
```

**Behaviour:**

1. Resolves the project folder as `<workspace_base_dir>/<project_id>`.
2. Validates the folder exists; returns `400` if not.
3. Enqueues a single Huey task that runs all three stages sequentially.
4. Returns immediately with a `pipeline_id`.

**Response** (JSON):

```json
{ "pipeline_id": "<uuid>" }
```

---

### `GET /status/<pipeline_id>`

Returns the current state of the pipeline, including the history of all
completed stages and the currently running stage.

**Response** (JSON):

```json
{
  "pipeline_id": "<uuid>",
  "done": true | false,
  "error": null | "<error message>",
  "stages": [
    {
      "name": "analyze" | "pack" | "deploy",
      "status": "pending" | "running" | "done" | "failed",
      "started_at": "<iso8601>" | null,
      "finished_at": "<iso8601>" | null,
      "stdout": "...",
      "stderr": "..."
    }
  ],
  "result": {
    "charm_file": "<absolute-path>.charm",
    "rock_file": "<absolute-path>.rock",
    "juju_model": "<uuid>",
    "juju_app": "<uuid>"
  }
}
```

**Stage ordering** is always `["analyze", "pack", "deploy"]`. The `stages`
array always contains all three entries; stages not yet reached have
`status: "pending"` and `null` timestamps.

**Rules:**
- `done` is `false` while any stage is `pending` or `running`.
- `result` is `null` until all three stages complete with `status: "done"`.
- `error` is non-null when a stage exits with a non-zero code or throws an
  exception. The failed stage entry will have `status: "failed"` and its
  `stderr` will contain the captured output.
- Stages completed before the failure retain `status: "done"` and their
  captured logs — the history is always preserved.

**Example — pack stage currently running:**

```json
{
  "pipeline_id": "a1b2c3",
  "done": false,
  "error": null,
  "stages": [
    {
      "name": "analyze",
      "status": "done",
      "started_at": "2026-05-12T08:00:00Z",
      "finished_at": "2026-05-12T08:02:30Z",
      "stdout": "Repo validated as charm-compatible.",
      "stderr": ""
    },
    {
      "name": "pack",
      "status": "running",
      "started_at": "2026-05-12T08:02:31Z",
      "finished_at": null,
      "stdout": "",
      "stderr": ""
    },
    {
      "name": "deploy",
      "status": "pending",
      "started_at": null,
      "finished_at": null,
      "stdout": "",
      "stderr": ""
    }
  ],
  "result": null
}
```

---

## Stage Definitions

### Stage 1 — Analyze

Runs an `opencode` agent to inspect the repository, verify it is conform, and
convert it to a valid charm repo if necessary.

```bash
opencode run "<instruction>"
```

- `cwd`: `<workspace_base_dir>/<project_id>`
- Success: exit code 0
- Output files: none (modifies repo in-place)

### Stage 2 — Pack

Runs `charmcraft pack` then `rockcraft pack` sequentially.

```bash
charmcraft pack
rockcraft pack
```

- `cwd`: `<workspace_base_dir>/<project_id>`
- Each command has a **10-minute timeout**
- Success: exit code 0 for both commands
- Output files: exactly **one** `.charm` file and **one** `.rock` file
  discovered by globbing the project directory after both commands complete

### Stage 3 — Deploy

Creates a dedicated Juju model and deploys the charm, then integrates it with
the existing HAProxy offer.

```bash
juju add-model <uuid>
juju deploy ./<charm-file> <uuid> --resource <rock-image> -m <uuid>
juju integrate <uuid> <haproxy-offer>
```

- `<uuid>` is the `pipeline_id`, used as both the Juju model name and app name
- `<rock-image>` is derived from the `.rock` file produced by the pack stage
- `<haproxy-offer>` is a snap configuration value (see below)
- Success: exit code 0 for all three commands

---

## Technology Stack

| Concern | Choice | Rationale |
|---|---|---|
| HTTP framework | **FastAPI** | Pydantic request validation, automatic OpenAPI docs at `/docs`, lightweight |
| ASGI server | **Uvicorn** | Minimal production-grade server for FastAPI |
| Task queue | **Huey** (`SqliteHuey`) | SQLite-backed broker *and* result store — no external broker needed |
| Persistence | **SQLite** (via Huey) | Embedded, zero external dependencies, correct fit for a snap |
| Command execution | **`subprocess` (stdlib)** | No extra dependency; blocking calls are fine inside Huey worker processes |

### Rejected alternatives

| Alternative | Reason rejected |
|---|---|
| Flask | FastAPI chosen for built-in validation and OpenAPI docs |
| Celery / RQ / Dramatiq | Require Redis or RabbitMQ — incompatible with a self-contained snap |
| `asyncio.create_subprocess_exec` | Unnecessary complexity; Huey workers are synchronous |
| `os.system()` / `shell=True` | No output capture / security risk |
| Separate services per stage | Identical structure; merged into one service with per-stage status reporting |

---

## Subprocess Execution Pattern

All stage commands follow the same pattern:

```python
result = subprocess.run(
    ["<command>", "<arg>", ...],
    cwd=project_path,
    capture_output=True,
    text=True,
    timeout=600,
)
```

The stage's `stdout` and `stderr` fields in the pipeline status are updated
**after each command completes**. If a command returns a non-zero exit code,
the stage is marked `failed`, its logs are saved, and the pipeline halts.

---

## Snap Configuration

| Key | Default | Description |
|---|---|---|
| `workspace-base-dir` | *(required)* | Absolute path to the directory containing project subdirectories |
| `haproxy-offer` | *(required)* | Juju cross-model offer URL for the shared HAProxy charm |

Read at runtime via `snapctl get`:

```python
result = subprocess.run(
    ["snapctl", "get", "workspace-base-dir"],
    capture_output=True, text=True, check=True,
)
workspace_base_dir = result.stdout.strip()
```

---

## Snap Process Layout

| Snap app | Command | Description |
|---|---|---|
| `api` | `uvicorn studio_agent.main:app` | Serves the FastAPI HTTP API |
| `worker` | `huey_consumer studio_agent.tasks.huey` | Processes enqueued pipeline tasks |

Both apps are declared in `snap/snapcraft.yaml` as systemd services and start
together.

**Host tool dependencies** (classic snap, accessed from host PATH):

- `opencode`
- `charmcraft`
- `rockcraft`
- `juju`

---

## Project Layout

```
studio_agent/
├── TDD.md           # This file
├── main.py          # FastAPI app, route definitions
├── tasks.py         # Huey instance + pipeline task definition
├── stages.py        # run_analyze(), run_pack(), run_deploy() stage functions
├── config.py        # Snap config helpers (snapctl get)
└── models.py        # Pydantic request/response models (pipeline schema)
snap/
└── snapcraft.yaml   # Snap packaging definition
```

---

## Future Considerations

- **Individual stage endpoints** — `POST /analyze`, `POST /pack`, `POST /deploy`
  for re-running a single stage without triggering the full pipeline.
- **Separate worker queues** — dedicate a Huey queue per stage type with tuned
  worker concurrency (analyze: CPU-heavy, deploy: I/O-bound).
- **Task cancellation** — `DELETE /pipeline/<pipeline_id>` to kill an
  in-progress subprocess.
- **Log streaming** — `GET /logs/<pipeline_id>` that tails live subprocess
  output before a stage completes.
- **Configurable timeout** — expose `pack-timeout` as a snap config key.
- **Workspace pre-validation** — check for `charmcraft.yaml` / `rockcraft.yaml`
  before enqueuing to fail fast.
