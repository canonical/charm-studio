# Allowed Rock Edits

Stay inside the extension.

## Usually Allowed

- name, summary, description, version, platforms
- build packages required for app dependencies
- stage packages or slices required at runtime
- extension-owned staged-file list adjustments
- a root `migrate.sh` when the app needs database migrations and the repo does
  not already expose a supported entrypoint
- service command overrides only after inspecting extension output
- extra service entries ending in `-worker` or `-scheduler` when the app needs
  background processes alongside the web service
- a small repo-backed startup wrapper or entrypoint shim when the app needs a
  minimal bridge from fixed `paas-charm` env names to its existing runtime
  contract
- `build-base` downgrade on `base: bare` for Python interpreter compatibility
- trial switch from `base: bare` to a supported Ubuntu base before deeper
  dependency changes when the initial build fails on bare
- plugin-backed frontend build parts when the app really ships one combined
  runtime image and the user explicitly confirmed that path

## Usually Not Allowed

- replacing the extension with a hand-maintained rock
- copying `expand-extensions` output and maintaining it manually
- bundling clearly separated frontend/backend monorepos into one image by
  default
- large project restructures just to satisfy the extension
- choosing embedded frontend/static builds without explicit user confirmation
- dependency upgrades before trying a compatible older `build-base` for Python
- over-broad staged file inclusion without evidence
- deep dependency edits on a `base: bare` failure before trying a supported
  Ubuntu base
- inventing worker or scheduler commands without repo evidence or user
  confirmation
- adding a duplicate migration path when the framework already manages it and
  the repo behavior is already clear
- using `rockcraft pack --destructive-mode` as a silent fallback

## Framework-Specific Reminders

- Flask and FastAPI `prime:` overrides are full replacement, not additive
- Django static asset preparation such as `collectstatic` belongs in the rock
  build, not the charm
- if a frontend is a separate build unit, prefer Rockcraft's built-in plugins
  for that frontend build instead of handwritten host-tool shell
- Go `assets.stage` overrides are full replacement, not additive
- Go service-command overrides may require an explicit `organize` mapping
- Spring Boot dual-build repos require a user-confirmed build-path choice
- ExpressJS must keep the app rooted under `app/`
- ExpressJS root-level repos can use a small trial-copy layout adaptation into
  `app/`
