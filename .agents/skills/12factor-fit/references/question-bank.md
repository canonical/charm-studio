# Inference Rules

These topics are resolved autonomously from repository inspection. No user
questions are asked. This file documents the inference logic for each concern.

## Fit And Intent

- **Framework**: use the top-scoring candidate from `detect_framework.py`.
  If two score equally, prefer the one with the stronger explicit signal
  (import statement > filename pattern > directory name).
- **Web service**: inspect source for web-framework route/listener patterns.
  If none found → hard stop with a clear error.
- **Monorepo backend root**: if a distinct `frontend/`, `ui/`, or `web/`
  subdirectory exists alongside backend source, scope to the backend
  subdirectory automatically.
- **Experimental extension acceptance**: auto-accept for FastAPI, Go,
  ExpressJS, Spring Boot. Note in the fit verdict output.

## Deployment Context

- Deployment context (registry, Kubernetes cluster, Juju controller, model)
  is handled by the studio_agent deploy stage. The fit skill does not need to
  resolve or validate these values.

## Runtime Behavior

- **Port**: infer from framework default (Flask/Django: 8080, FastAPI: 8080,
  ExpressJS: `PORT` env or 3000, Go: infer from `http.ListenAndServe` call,
  Spring Boot: `server.port` or 8080). Record in output notes.
- **Charm config options**: infer from `requirements.txt`, `pyproject.toml`,
  environment variable reads in source, and config files. Flag obvious secrets
  (anything named `*_KEY`, `*_SECRET`, `*_PASSWORD`, `*_TOKEN`).
- **Frontend build**: if a distinct frontend subdirectory exists →
  `separate-deployment`; if a frontend build step is embedded in a
  single-runtime app → `embedded-in-backend-image`; otherwise → `none`.
- **Database migrations**:
  - `manage.py` present → `framework-managed, tool: manage.py`
  - `migrate.sh` / `migrate.py` / `migrate` at repo root → `migrate-sh`
  - Flask-Migrate, Alembic, or other migration library in requirements without
    an existing entrypoint → `migrate-sh` (add `migrate.sh`)
  - Flyway / Liquibase in Spring Boot → `framework-managed`
  - No database dependency → `none`
- **Workers and schedulers**: inspect `Procfile`, `docker-compose.yml`,
  `supervisord.conf`, and README for named process entries. Use `-worker` for
  always-on processes, `-scheduler` for single-unit cron-style processes.
- **Relations**: map dependency signals to Juju relations. Default all to
  `optional: true` except postgresql/mysql when the app has no alternative
  data store → `optional: false`.
- **Ingress**: always set `needed: true`; `external_hostname: null` (resolved
  at deploy time).

## Layout Adaptation

- Framework extension expects the app under a specific path. If the repo does
  not match, apply the smallest trial-copy layout adaptation automatically and
  note it in the fit verdict. Do not ask for confirmation.
