# Framework Rock Contracts

Use this file before editing `rockcraft.yaml`.

## Profile Names

Use these exact `rockcraft init --profile ...` values:

| Framework | Profile |
| --- | --- |
| Flask | `flask-framework` |
| Django | `django-framework` |
| FastAPI | `fastapi-framework` |
| Go | `go-framework` |
| ExpressJS | `expressjs-framework` |
| Spring Boot | `spring-boot-framework` |

## Experimental Extension Reminder

FastAPI, Go, ExpressJS, and Spring Boot currently rely on experimental
extensions.

- use an edge-channel `rockcraft`
- export `ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true`
- stop and confirm before promising this path if the user does not accept that tradeoff

## Migrations And Background Services

- Current `paas-charm` migration precedence is `migrate`, then `migrate.sh`,
  then `migrate.py`, then `manage.py`, with the last match winning.
- Flask, FastAPI, ExpressJS, and Go support a root `migrate.sh` directly.
- If one of those apps needs database migrations and the repo does not already
  expose a supported migration entrypoint, add a small root `migrate.sh` that
  delegates to the app's existing migration tool.
- Keep `migrate.sh` idempotent and safe to run on multiple units.
- Django also supports migrations, but current `paas-charm` code will use
  `manage.py migrate` whenever `manage.py` exists. Do not generate
  `migrate.sh` expecting it to override Django's native path.
- Spring Boot should normally rely on framework-managed migrations such as the
  repo's existing Flyway or Liquibase path instead of generating `migrate.sh`.
- Extra `rockcraft.yaml` services whose names end in `-worker` or
  `-scheduler` receive the same environment as the main application.
- `-worker` services run on all units. `-scheduler` services run on only one
  unit, so use that naming deliberately.

## Pebble Runtime Sanity Check

- inspect the effective expanded Pebble service command, user, and working
  directory before packing, especially after overriding service commands or
  adding files under `/app`
- if the application mutates a file or directory at startup and the service
  runs as a non-root user such as `_daemon_`, ensure that target is writable by
  the runtime user or relocate that mutable state to a more appropriate
  writable path
- if the application binary is really a multi-command CLI, make the Pebble
  service command invoke the intended long-running subcommand instead of the
  bare top-level binary

## Flask

- Rockcraft extension: `flask-framework`
- Runtime style: Gunicorn
- Current experimental status in code: false
- Accepted bases in code: `bare`, `ubuntu@22.04`, `ubuntu:22.04`, `ubuntu@24.04`
- Contract:
  - `requirements.txt` or `pyproject.toml`
  - Flask dependency present
  - discoverable WSGI entrypoint unless the service command is overridden
- Practical lessons:
  - requirement includes such as `-r requirements/*.txt` are common and should
    be parsed in fit checks
  - realistic Flask apps may need extra staged runtime files such as
    `config.py`, `migrations/`, or `migrate.sh`

## Django

- Rockcraft extension: `django-framework`
- Runtime style: Gunicorn
- Current experimental status in code: false
- Accepted bases in code: `bare`, `ubuntu@22.04`, `ubuntu:22.04`, `ubuntu@24.04`
- Contract:
  - root `requirements.txt`
  - runtime app under `<repo>/<project-name>/`
  - supported `wsgi.py` location under that runtime directory
  - discoverable `application` object unless the service command is overridden
- Practical lessons:
  - realistic repos often need a trial-copy layout adaptation to match the
    extension’s directory expectations
  - if Python dependencies compile native code, add only the missing
    `build-packages` to `django-framework/dependencies`
  - if `pyproject.toml` plus `charm/` causes `pip install .` to fail, treat it
    as a build-tooling interaction and make the smallest explicit workaround
  - if the app needs migrations, rely on `manage.py migrate` when `manage.py`
    is present; do not add `migrate.sh` expecting it to override that path
  - if the app needs `collectstatic` or another static/frontend build step, do
    that work in the rock build, not in the charm
  - extension-part tuning is acceptable here; replacing the extension with a
    hand-maintained rock is not

## FastAPI

- Rockcraft extension: `fastapi-framework`
- Runtime style: Uvicorn
- Current experimental status in code: true
- Accepted bases in code: `bare`, `ubuntu@24.04`
- Contract:
  - root `requirements.txt`
  - `fastapi` or `starlette` in requirements
  - discoverable ASGI `app` object unless the service command is overridden
- Important:
  - on `base: bare`, Python comes from `build-base`
  - `ubuntu@22.04` gives Python `3.10`
  - `ubuntu@24.04` gives Python `3.12`

## ExpressJS

- Rockcraft extension: `expressjs-framework`
- Runtime style: `npm start`
- Current experimental status in code: true
- Accepted bases in code: `bare`, `ubuntu@24.04`
- Contract:
  - `app/package.json`
  - `package.json.name`
  - `package.json.scripts.start`
- Practical lessons:
  - root-level Express repos are still valid fit candidates, but the rock
    contract requires an explicit move or adaptation into `app/`
  - on `base: bare`, the extension already stages Node and npm by default
  - be careful with app code that forces TLS just because a database URL is set
  - if the repo is really one Node runtime with frontend and backend source
    trees inside it, a frontend build step in the extension-owned install part
    is acceptable

## Go

- Rockcraft extension: `go-framework`
- Runtime style: compiled binary
- Current experimental status in code: true
- Accepted bases in code: `bare`, `ubuntu@24.04`
- Contract:
  - root `go.mod`
  - service command defaults to the rock name
  - extra assets go through `go-framework/assets`
- Practical lessons:
  - if you override `services.go.command`, the extension stops auto-adding the
    default binary organize rule
  - when the main package directory name differs from the rock name, add the
    explicit `go-framework/install-app.organize` mapping instead of manualizing
    the rock
  - Go binaries are often multi-command CLIs, so a bare command equal to the
    rock name may print usage and exit unless the repo's real runtime subcommand
    is set explicitly
  - if startup writes generated config or other mutable state under `/app`,
    make that target writable by the Pebble runtime user instead of leaving it
    root-only in the packed image

## Spring Boot

- Rockcraft extension: `spring-boot-framework`
- Runtime style: fat jar
- Current experimental status in code: true
- Accepted bases in code: `bare`, `ubuntu@24.04`
- Contract:
  - exactly one active build system
  - `pom.xml` or `build.gradle`, not both
  - `mvnw` or `gradlew`, not both
  - wrapper scripts executable if present
- Practical lessons:
  - wrapper scripts such as `mvnw` or `gradlew` must be executable before build
  - dual-build-system repos need explicit user confirmation of which build path
    to keep in the trial copy
  - the fat-jar model means no extra runtime dependency management is normally
    required in the rock
  - prefer the repo's framework-managed migration path instead of generating a
    new `migrate.sh`
  - `application.properties` and `application.yml` are the natural place to
    bridge env-driven runtime config

## Static And Frontend Build Rule

For any supported framework:

- if the repo clearly separates frontend and backend into different
  subdirectories, apply the 12-factor workflow to the backend subdirectory
  instead of trying to bundle both into one image
- if the repo has a frontend or static-asset build step, ask the user
  explicitly whether it belongs inside this rock build or remains a separate
  deployment concern
- if the app still intentionally ships one combined runtime image, run the
  frontend build in the rock build only after that user confirmation
- prefer Rockcraft plugin-backed frontend parts, especially `npm`, when the
  frontend is a distinct build unit
- if the app needs static assets prepared for runtime, do that in the rock
- do not push static-asset compilation into deploy-time charm behavior

## `base: bare` Failure Rule

For frameworks that support both `base: bare` and a supported Ubuntu base:

- if `rockcraft pack` fails on `base: bare`, try the supported Ubuntu base
  first before deeper dependency changes
- only move into dependency upgrades or larger dependency edits after that
  Ubuntu-base trial also fails or the framework contract does not allow it

## Rock Push Rule

- prefer Rockcraft-shipped `skopeo` at `/snap/rockcraft/current/bin/skopeo`
  when an OCI archive needs to be copied into a registry
- if the host does not provide a containers policy file, add
  `--insecure-policy` explicitly rather than switching to unrelated tooling
- do not introduce ad hoc external container images just to move the rock

## Python Packaging Warning

For Flask, Django, and FastAPI:

- if the repo contains `setup.py` or `pyproject.toml`
- the Craft Python plugin will try to install the local project
- if the repo also contains `charm/`, project-metadata discovery can fail in
  ways unrelated to the application runtime

Treat that as a preflight requirement, not a surprise during build.
