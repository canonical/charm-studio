# `paas-charm` Runtime Notes

Generated 12-factor charms are `paas-charm` charms.

## Shared Runtime Behavior

`paas-charm` owns:

- readiness gating
- ingress publication
- secret handling and rotation
- migration execution
- relation-driven env generation
- supported relation env injection into the workload
- Pebble layer overlay
- observability wiring

## Rock-Defined Service Env

Treat `paas-charm` as the component that owns the final Pebble layer seen by
the workload.

- env set under `services.*.environment` in `rockcraft.yaml` should not be
  assumed to survive unchanged once the app runs under the charm
- if the rock relies on those env vars, mirror the required keys into the
  charm-managed workload contract as part of the charm adaptation
- prefer non-conflicting charm config defaults when the value should remain
  operator-visible
- prefer a tiny workload-side defaulting wrapper or entrypoint shim when the
  value is a static app-facing default and adding charm Python would be excess

## Pebble Failure Triage

- if Juju debug logs show Pebble service exit loops with CLI usage output,
  treat that as a rock service-command problem first
- if Juju debug logs show `permission denied` on workload paths such as `/app`,
  treat that as a rock filesystem-layout or runtime-user problem first
- inspect the rock's effective Pebble command, user, working directory, and
  writable paths before treating those failures as a reason to customize
  `src/charm.py`

## Migration Order

`paas-charm` checks for migrations in this effective order:

1. `manage.py`
2. `migrate.py`
3. `migrate.sh`
4. `migrate`

Treat migration naming as part of the supported contract.

### Django Migration Precedence Note

Because Django repos normally have `manage.py`, adding a repo `migrate.sh` does
not replace the default migration path. `paas-charm` will still prefer
`manage.py migrate`.

## Env Prefix Differences

Treat these emitted env families as the baseline runtime contract. If the
application expects different names, or the rock already relied on extra
service env, prefer a workload-side bridge or charm-managed mirror instead of
editing charm Python.

### Flask And Django

- built-in and user-defined config env use `FLASK_` or `DJANGO_`
- observability defaults are Gunicorn/statsd based

### FastAPI

- built-in framework env is mostly unprefixed
- user-defined config uses `APP_*`
- JSON structured logging support exists in current `paas-charm`

### Go

- built-in and user-defined config env use `APP_*`

### ExpressJS

- framework config env is intended to be mostly unprefixed
- user-defined config uses `APP_*`
- verify the `app-port` versus `port` alias mismatch before promising a clean path

### Spring Boot

- built-in env is mostly unprefixed
- relation env is heavily translated into Spring property names such as:
  - `spring.datasource.url`
  - `spring.data.redis.url`
  - `spring.security.oauth2.*`
  - `management.endpoints.web.*`

## OAuth And OIDC Note

- supported OAuth or OIDC relations already inject runtime data into the
  workload environment through `paas-charm`
- when the generated framework exposes deploy-time config such as
  `<endpoint>-redirect-path`, prefer that over charm subclassing
- do not add custom relation listeners or override relation methods just to
  rename relation env vars or tweak defaults

## Observability Differences

- Flask and Django metrics come through the Gunicorn/statsd exporter path
- FastAPI, Go, ExpressJS, and Spring Boot use workload-defined metrics target and path
- current JSON logging support is implemented only for FastAPI, Flask, and Django
