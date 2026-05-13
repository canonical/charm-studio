# Charm Studio

HTTP API service that orchestrates the full repo-to-deployment pipeline for 12-factor charm applications. Point it at a Git repository and it automatically verifies compatibility, generates a Juju charm and OCI rock, packs them, and deploys them to Kubernetes with HAProxy ingress -- all through a web UI.

> **Status:** Early development (v0.1). Grade: devel.

## Architecture

Charm Studio has two components:

- **Backend** (`studio_agent/`) -- FastAPI service that exposes a REST API and runs an async pipeline via Huey workers.
- **Frontend** (`frontend/`) -- React SPA built with Vite, using Canonical's Vanilla Framework.

Both are packaged as a single **snap** for production, with two daemons: `charm-studio.api` and `charm-studio.worker`.

The pipeline uses `opencode` CLI with three AI agent skills:

1. **12factor-fit** -- Pre-flight check: is this repo compatible?
2. **12factor-charm** -- Generate Juju charm files.
3. **12factor-rock** -- Generate OCI rock (container image) files.

## Pipeline Stages

```
POST /pipeline  { source: { url, branch, credentials } }
         │
         ▼
  1. CLONE   ── git clone into workspace
  2. VERIFY  ── opencode run /12factor-fit
  3. CHARM + ROCK (parallel)
     ├─ opencode run /12factor-charm → charmcraft pack
     └─ opencode run /12factor-rock  → rockcraft pack
  4. DEPLOY
     ├─ Push rock to registry
     ├─ juju deploy .charm with OCI resource
     └─ juju integrate haproxy-route via ingress-configurator
```

The frontend polls `GET /status/{pipeline_id}` every 2 seconds and renders stage progress, logs, and results in real time.

## Prerequisites

### Runtime (pipeline execution)

- `opencode` CLI with the 12factor-fit, 12factor-charm, and 12factor-rock skills installed
- `juju` -- Juju CLI
- `charmcraft` -- for packing charms
- `rockcraft` -- for packing rocks
- `rockcraft.skopeo` -- for pushing rock images to a registry
- A bootstrapped Juju controller with a Kubernetes cloud registered

### Development

- Python 3.12+
- Node.js (with npm)

## Local Development

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r studio_agent/requirements.txt -r requirements-dev.txt -r requirements-test.txt
```

Start the API server:

```bash
uvicorn studio_agent.main:app --host 0.0.0.0 --port 8000
```

In a separate terminal, start the Huey worker:

```bash
python -m huey.bin.huey_consumer studio_agent.tasks.huey -w 4
```

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies API requests to the backend.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `WORKSPACE_BASE_DIR` | `/tmp/charm-studio-workspace` | Directory for cloned repos and build artifacts |
| `PORT` | `8000` | API server port |
| `HAPROXY_OFFER` | *(required for deploy)* | Juju cross-model offer URL for HAProxy |
| `REGISTRY` | `localhost:32000` | OCI registry for rock images |
| `APP_PROFILES` | *(none)* | App profile config passed to `juju deploy` |

## Testing

### Backend

```bash
pytest -q
```

Tests live in `studio_agent/tests/` and `tests/`. They use FastAPI's `TestClient` with mocked subprocess calls.

### Frontend

```bash
cd frontend
npm test            # single run
npm run test:watch  # watch mode
```

### Linting & Type Checking

```bash
ruff check studio_agent/
mypy studio_agent/
```

```bash
cd frontend && npx tsc --noEmit
```

## Deployment

### Snap (recommended for production)

Build and install the snap:

```bash
snapcraft
sudo snap install charm-studio_*.snap --classic --dangerous
```

Configure the snap:

```bash
sudo snap set charm-studio \
  port=8000 \
  workspace-base-dir=/var/snap/charm-studio/common/workspace \
  haproxy-offer="<controller>:admin/haproxy.haproxy-route" \
  registry=localhost:32000
```

The snap runs two daemons:
- `charm-studio.api` -- FastAPI + Uvicorn serving the API and static frontend
- `charm-studio.worker` -- Huey task consumer (4 workers)

Check status:

```bash
snap services charm-studio
```

View logs:

```bash
snap logs charm-studio.api
snap logs charm-studio.worker
```

### Infrastructure provisioning

The `deployment/` directory contains everything needed to set up a Kubernetes cloud and HAProxy ingress. This is required before deploying any pipelines.

1. Install concierge and the required snaps/packages:

```bash
sudo snap install concierge
sudo concierge prepare -c deployment/concierge.yaml
```

2. Run the provisioning script to register the k8s cloud, deploy HAProxy and Lego (TLS), and create the cross-model offer:

```bash
bash deployment/provision.sh
```

The script will:
- Register a `ck8s` Kubernetes cloud with Juju
- Deploy the `haproxy` charm in a dedicated model
- Deploy the `lego` charm for OVH DNS-01 TLS certificates (requires `OVH_ENDPOINT`, `OVH_APPLICATION_KEY`, `OVH_APPLICATION_SECRET`, `OVH_CONSUMER_KEY` in `~/.bashrc`)
- Integrate Lego with HAProxy for automatic TLS
- Create a cross-model offer for `haproxy-route`
- Apply a local OCI registry config to the k8s cluster

After provisioning, set the HAProxy offer URL in the snap:

```bash
sudo snap set charm-studio haproxy-offer="<controller>:admin/haproxy.haproxy-route"
```

## Workflow

1. Open Charm Studio in your browser (default `http://localhost:8000`).
2. On the **Import** page, enter a Git repository URL and optional branch/credentials.
3. Click **Start** -- a pipeline is created and you're redirected to the pipeline view.
4. Watch the four stages progress in real time: verify, charm + rock, pack, deploy.
5. Logs appear in terminal-style panels (green for stdout, red for stderr).
6. When complete, the result banner shows the charm path, rock image, Juju model, and deployed app name.
7. Past pipelines appear in the **sidebar** (persisted in localStorage, max 20 entries).
8. To re-deploy an already-built workspace, use the **Deploy** endpoint directly.
9. To cancel a running pipeline, click **Cancel** (or call `DELETE /pipeline/{id}`).

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/pipeline` | Start a new pipeline. Body: `{ source: { url, branch?, credentials? } }`. Returns `201` with `pipeline_id`. |
| `GET` | `/status/{pipeline_id}` | Get pipeline status with all stages, logs, and result. |
| `DELETE` | `/pipeline/{pipeline_id}` | Cancel a running pipeline. Returns `204`, or `409` if already done. |
| `POST` | `/deploy` | Re-run deploy stage only. Body: `{ pipeline_id, workspace_dir }`. Returns `202`. |

## Project Structure

```
studio_agent/          Backend: FastAPI pipeline service
  main.py              App and route definitions
  tasks.py             Huey task definitions
  stages.py            Stage runners (clone, verify, charm, rock, pack, deploy)
  models.py            Pydantic models
  config.py            Configuration (snapctl / env vars)
  tests/               Backend unit tests
frontend/             Frontend: React SPA
  src/
    components/        ImportView, PipelineView, Sidebar, NavigationBar
    hooks/             usePipelineStatus, useHistory
    api/               HTTP client wrappers
    types.ts           TypeScript interfaces
deployment/           Infrastructure provisioning
  concierge.yaml       Concierge provider config
  provision.sh         Full provisioning script
snap/                 Snap packaging
  snapcraft.yaml       Snap build definition
  hooks/               install, configure, post-refresh
.agents/skills/       AI agent skills for opencode
.stitch/              Design system and generated mockups
```

## License

This project is proprietary software.
