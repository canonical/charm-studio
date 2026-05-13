# Framework Charm Contracts

Use this file after `charmcraft init` and before changing `charmcraft.yaml`.

## Profile Names

Use these exact `charmcraft init --profile ...` values:

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

- use an edge-channel `charmcraft`
- export `CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true`
- stop and confirm before promising this path if the user does not accept that tradeoff

## Shared Rules

- create the charm in `charm/`
- always generate files via `charmcraft init --profile <framework> --name <name>` — never copy from templates, previously generated files, or example charms
- inspect generated files instead of assuming older template contents
- the extension already declares ingress (required), grafana-dashboard (optional), metrics-endpoint (optional), and logging (optional) — do not re-declare these and do not ask the user about their optionality
- add only user-confirmed relations beyond those already provided by the extension
- set each declared relation's `optional` field from explicit user input or fit
  handoff
- do not infer required versus optional from repo inspection or app behavior
- add only non-conflicting config options
- remember that generated charms subclass `paas-charm` framework classes
- treat generated `paas-charm` env output and relation env injection as the
  baseline contract
- if `rockcraft.yaml` already defines service env, carry forward the required
  keys into the charm-managed workload contract too
- keep generated `src/charm.py` stock unless there is no viable workload-side
  adaptation and the user explicitly approved changing charm source
- pack with `charmcraft pack`, never `--destructive-mode`

## Minimal YAML Examples

Add a database relation only when the user confirmed it belongs in the charm,
and set `optional` from the user's answer:

```yaml
requires:
  postgresql:
    interface: postgresql_client
    optional: false
```

Add an optional relation only when the user explicitly wants it declared as
optional:

```yaml
requires:
  openid:
    interface: oauth
    optional: true
```

Add a non-conflicting plain config option:

```yaml
config:
  options:
    log-path:
      type: string
      default: /tmp/logs
      description: Filesystem path for application log output.
```

Add a secret-type config option:

```yaml
config:
  options:
    oidc-client-secret:
      type: secret
      description: OIDC client secret for the upstream app.
```

## OAuth And OIDC Relations

- declared OAuth or OIDC relations already participate in built-in
  `paas-charm` relation handling and workload env injection
- prefer deploy-time config such as `<endpoint>-redirect-path` when the
  generated framework config exposes it
- do not add custom relation hook listeners or override relation methods just
  to rename env vars or tweak relation-provided defaults

## Flask

- Charmcraft extension: `flask-framework`
- Current experimental status in code: false
- Built-in config surface includes Gunicorn options plus Flask-specific settings
- Built-in env shape is mostly `FLASK_*`

## Django

- Charmcraft extension: `django-framework`
- Current experimental status in code: false
- Built-in config surface includes Gunicorn options, `django-debug`, `django-secret-key`, `django-allowed-hosts`
- Built-in action surface includes `create-superuser`
- Built-in env shape is mostly `DJANGO_*`
- Practical lessons:
  - built-in config is the preferred way to handle `django-secret-key` and
    `django-allowed-hosts`
  - current `paas-charm` Django behavior prefers `manage.py migrate` whenever
    `manage.py` exists
  - do not rely on a repo `migrate.sh` to force static asset work
  - if the app needs `collectstatic`, prefer doing it in the rock build and
    keep the generated charm simple
  - avoid overriding private or semi-private `paas-charm` internals

## FastAPI

- Charmcraft extension: `fastapi-framework`
- Current experimental status in code: true
- Built-in config surface includes `webserver-workers`, `webserver-port`, `webserver-log-level`, `metrics-*`, `app-secret-key`
- Built-in env shape is mostly unprefixed framework variables plus `APP_*` for user config

## ExpressJS

- Charmcraft extension: `expressjs-framework`
- Current experimental status in code: true
- Built-in config surface includes `app-port`, `metrics-*`, `app-secret-key`
- Known mismatch with current `paas-charm` ExpressJS aliases: verify at execution time
- Practical lessons:
  - adding a non-conflicting `port` config option is an acceptable bridge
  - this is preferable to changing generated charm code

## Go

- Charmcraft extension: `go-framework`
- Current experimental status in code: true
- Built-in config surface includes `app-port`, `metrics-*`, `app-secret-key`
- Built-in env shape is `APP_*`
- Practical lessons:
  - relation-provided database URLs often need a small workload-side alias to the
    repo’s existing config key

## Spring Boot

- Charmcraft extension: `spring-boot-framework`
- Current experimental status in code: true
- Built-in config surface includes `app-port`, `app-profiles`, `metrics-*`, `app-secret-key`
- Default metrics path is `/actuator/prometheus`
- Runtime env shape includes both generic env and Spring-style property env

## Django Reminder

- the generated Django charm already provides useful built-in config:
  - `django-secret-key`
  - `django-allowed-hosts`
- prefer consuming those in the workload config layer over inventing parallel charm
  options
