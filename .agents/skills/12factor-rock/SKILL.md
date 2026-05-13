---
name: 12factor-rock
description: >
  Creates or adapts a Canonical 12-factor rock while staying inside the
  Rockcraft extension contract. Validates framework-specific rock fit, keeps
  edits minimal, preserves extension boundaries, and guides build and registry
  push work.
  WHEN: create rockcraft yaml, adapt existing rock, validate rock contract, run
  rockcraft init, inspect expand-extensions, add migration entrypoint, define
  worker or scheduler service, push OCI image to registry, create a rock for a
  12-factor application.
license: Apache-2.0
metadata:
  author: Canonical/platform-engineering
  version: "1.0.0"
  summary: Create a rock, configure the entrypoint and services, add required files/dependencies, then hand off packaging to the studio agent.
  tags:
    - canonical
    - 12-factor
    - rockcraft
    - oci
    - packaging
    - pebble
    - registry
---

# 12factor Rock

Stay inside the extension. If the repo only works after replacing the extension, stop.

## Skill Order

- Run `$12factor-fit` first when possible.
- Run this skill before `$12factor-juju-terraform`.
- This skill and `$12factor-charm` can proceed independently once the fit
  verdict, framework, and target context are clear.

## Workflow

1. Reuse the fit verdict from `$12factor-fit` if available. If not, inspect the repo and confirm the framework yourself.
2. Run `scripts/check_rock_contract.py <repo> --framework <framework>` before generating anything.
3. Load `references/framework-rock-contracts.md` for the exact project contract of the chosen framework.
4. If the framework is FastAPI, Go, ExpressJS, or Spring Boot, auto-accept the
   experimental extension path. Ensure `rockcraft` is on an edge channel with
   `ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true` and proceed. Note the
   experimental acceptance in the output.
5. If the repo clearly separates frontend and backend in a monorepo, automatically
   set the backend subdirectory as the target scope before running
   `rockcraft init`. Note the automatic scoping in the output.
6. **Auto-decide frontend build**: If the repo has no distinct frontend
   subdirectory but contains a frontend build step embedded in a single-runtime
   app, run that build inside this rock. If a distinct frontend subdirectory
   exists, keep that concern separate and note it in the output. Do not create
   a combined frontend+backend image for clearly separated repos.
7. If the project does require a frontend build inside the same rock, prefer a
   Rockcraft plugin-backed build part when the frontend is a distinct build
   unit. Only use shell steps inside an extension-owned part when the frontend
   is already part of the same runtime application surface.
8. If the app needs database migrations, prefer a root `migrate.sh` for Flask,
   FastAPI, ExpressJS, and Go when the repo does not already provide a
   supported migration entrypoint. For Django, remember current
   `paas-charm` code uses `manage.py migrate` whenever `manage.py` exists, so a
   new `migrate.sh` will not replace that path. For Spring Boot, prefer
   framework-managed migrations unless the repo already exposes a compatible
   wrapper.
9. If the app needs extra background services, add `rockcraft.yaml` services
   whose names end in `-worker` or `-scheduler`, using repo-backed or
   user-confirmed commands only.
10. Run the exact profile from `references/framework-rock-contracts.md`, for
   example `rockcraft init --profile fastapi-framework`. Always use this
   command to generate `rockcraft.yaml` — never copy from templates,
   previously generated files, or example rocks.
11. Inspect the generated `rockcraft.yaml`.
12. Run `rockcraft expand-extensions` before making non-trivial edits.
13. If you add or override Pebble services, inspect the effective expanded
    service command, user, and working directory before packing.
14. If the service runs as a non-root user such as `_daemon_`, verify any file
    or directory the app may create, rewrite, or persist at startup is
    writable by that runtime user, or relocate that mutable state to a more
    appropriate writable path.
15. If the application binary is a multi-command CLI, make the Pebble service
    command invoke the actual long-running subcommand (`server`, `worker`,
    etc.) instead of the bare top-level CLI.
16. Keep edits inside extension-owned parts and the minimal metadata fields described in `references/allowed-edits.md`.
17. Do not run `rockcraft pack` in this skill. Hand off packaging to the
    studio agent, which runs `rockcraft pack` after this skill completes.
18. Registry push is handled by the studio_agent deploy stage — do not push or
    ask about push.

## Allowed Changes

- set name, summary, description, version, and platforms
- add build or stage packages the app truly needs
- add required staged files the extension does not already include
- tune extension-owned parts
- add a root `migrate.sh` when the app needs database migrations and the repo
  does not already expose a supported entrypoint
- add `rockcraft.yaml` services ending in `-worker` or `-scheduler` when the
  app needs background services alongside the main web service
- add a small repo-backed startup wrapper or entrypoint shim in the workload
  image when the app needs a minimal bridge from fixed `paas-charm` env names
  to its existing runtime contract
- adjust ownership or mode of runtime-mutated files or directories inside
  extension-owned parts when the workload runs as a non-root user and needs
  write access at startup
- run frontend builds or static-asset preparation steps in the rock build when
  the application has no distinct frontend subdirectory (i.e., the frontend is
  embedded in the single-runtime app)
- add a dedicated plugin-backed frontend build part when the frontend is a
  distinct build unit inside the same application scope with no separate
  frontend subdirectory
- when `base: bare` build fails, try a supported Ubuntu base before deeper
  dependency changes
- move `build-base` to an older supported Ubuntu release when `base: bare`
  allows it and the failure is interpreter compatibility

## Disallowed Changes

- do not rewrite the rock from `expand-extensions` output
- do not create a bespoke manual rock as a silent fallback
- do not generate `rockcraft.yaml` by copying from templates, previously generated files, or example rocks — always use `rockcraft init --profile <framework>`
- do not default to bundling clearly separated frontend and backend monorepos
  into one image
- do not widen the staged file set unless the extension contract actually requires it
- do not choose embedded frontend/static builds for clearly separated repos;
  embed only when there is no distinct frontend subdirectory
- do not upgrade app dependencies before trying an older supported `build-base` for Python framework rocks
- do not jump straight into dependency upgrades or deep dependency edits on a
  `base: bare` failure before trying a supported Ubuntu base
- do not invent worker or scheduler commands without repo evidence (Procfile,
  docker-compose, supervisor config, README process entries)
- do not add a duplicate migration path when the framework already manages it
  and the intended repo behavior is clear
- do not move static-asset or frontend build work into the charm when it can be
  done at rock build time
- do not use `rockcraft pack --destructive-mode`; stop with a clear error if
  the standard build path is blocked for reasons other than base compatibility

## Framework Rules

Use `references/framework-rock-contracts.md` every time. The important differences are:

- Flask and Django are Gunicorn-based
- FastAPI is Uvicorn-based
- ExpressJS requires `app/package.json`
- Go is binary-first and uses separate assets staging
- Spring Boot requires one active build system only
- `-worker` and `-scheduler` service names control how 12-factor charms run
  extra services

## Output Contract

Produce:

- a minimal `rockcraft.yaml`
- a clear list of any repo or layout adaptations that were required, including
  automatic decisions made (monorepo scoping, frontend handling, experimental
  extension acceptance)
- a rock layout ready for `rockcraft pack` by the studio agent
- an explicit note if the repo does not fit the supported extension path
