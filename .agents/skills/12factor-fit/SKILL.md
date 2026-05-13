---
name: 12factor-fit
description: >
  Assesses whether a repository fits Canonical's 12-factor rock, charm, Juju,
  and Terraform workflow before generating artifacts. Confirms framework fit,
  web-service scope, Kubernetes suitability, deployment context, relation
  optionality, and preflight readiness so later skills do not guess.
  WHEN: assess repository fit, 12-factor fit check, detect framework, confirm
  web app scope, verify Kubernetes-backed deployment, gather deployment
  context, capture relation optionality, preflight cluster controller and
  registry, stop unsupported project early.
license: Apache-2.0
metadata:
  author: Canonical/platform-engineering
  summary: Analyze the existing project, detect the framework, and assess the compatibility with the 12-factor with Rockcraft, Charmcraft, and Juju / Terraform deployment
  version: "1.0.0"
  tags:
    - canonical
    - 12-factor
    - fit
    - rockcraft
    - charmcraft
    - juju
    - terraform
---

# 12factor Fit

Inspect first. Infer everything from the repository. Do not ask the user questions.

## Skill Order

- Run this skill first.
- Hand off to `$12factor-rock` and `$12factor-charm` only after the fit verdict
  is explicit.

## Workflow

1. Inspect the repository thoroughly before doing anything else.
2. Run `scripts/detect_framework.py <repo>` to get a framework verdict with signals.
3. **Auto-select framework**: Use the top-scoring candidate automatically. If
   two candidates score equally, pick the one supported by stronger explicit
   signals (e.g., framework import in source over an ambiguous filename). Note
   any ambiguity in the fit verdict output but do not stop.
4. **Auto-confirm web service**: Inspect the source for web-framework signals
   (Flask `app = Flask(...)`, Django `urlpatterns`, FastAPI `@app.get`/`@app.post`,
   Express `app.listen`, Go `http.ListenAndServe`, Spring Boot `@RestController`
   or `@Controller`). If none are found after inspection, stop with a clear
   error: "No web entrypoint detected — this does not appear to be a web
   service."
5. **Auto-scope monorepo**: If the repo clearly separates frontend and backend
   into different subdirectories (e.g., `frontend/`, `ui/`, `web/` alongside a
   distinct backend directory or the repo root), automatically set `repo_path`
   to the backend subdirectory and record `frontend_build: separate-deployment`.
   Do not bundle both into one image.
6. **Auto-decide frontend build**: If the repo is a single-runtime application
   with a frontend or static-asset build step embedded in it (no separate
   frontend subdirectory), set `frontend_build: embedded-in-backend-image` and
   plan to run that build inside the rock. Otherwise set
   `frontend_build: separate-deployment` or `none`.
7. **Auto-infer migrations**: Check for migration evidence in this order:
   - `manage.py` present → `mode: framework-managed, tool: manage.py`
   - `migrate.sh` or `migrate.py` or `migrate` present at repo root → `mode: migrate-sh, tool: <found file>`
   - Flask-Migrate or Alembic in `requirements.txt`/`pyproject.toml`, or
     a known migration library without an existing entrypoint → `mode: migrate-sh, tool: null` (add `migrate.sh`)
   - Flyway or Liquibase in Spring Boot build file → `mode: framework-managed, tool: flyway/liquibase`
   - No database dependency detected → `mode: none, tool: null`
8. **Auto-infer workers and schedulers**: Inspect `Procfile`, `docker-compose.yml`,
   `supervisord.conf`, process manager configs, and README for process entries
   whose names or roles suggest background workers or schedulers. Capture their
   commands verbatim. Use `-worker` suffix for always-on processes and
   `-scheduler` suffix for single-unit scheduled processes.
9. **Auto-infer relations**: Inspect `requirements.txt`, `pyproject.toml`,
   `package.json`, `go.mod`, `pom.xml`, and `build.gradle` for dependency
   signals. Map common dependencies to relations:
   - psycopg2, psycopg, asyncpg, pg, postgresql driver → `postgresql` relation
   - redis, aioredis → `redis` relation
   - pika, amqp, kombu → `rabbitmq` relation
   - boto3, minio → `s3` relation
   - authlib, python-jose, requests-oauthlib → `oauth` relation
   Default all inferred relations to `optional: true` **except** postgresql and
   mysql when the app code has no fallback data store — set those to
   `optional: false`.
10. **Auto-accept experimental extensions**: If the framework is FastAPI, Go,
    ExpressJS, or Spring Boot, set `experimental_extensions_accepted: true`
    automatically. Note this in the fit verdict output.
11. Load `references/framework-detection.md` and `references/known-risks.md`
    before finalising the verdict.
12. Produce the fit verdict with:
    - detected framework
    - structured handoff payload
    - notes on any automatic decisions made (monorepo scoping, frontend handling,
      experimental extension acceptance)
    - explicit stop reason if the project does not fit

## Non-Negotiables

- Detect the framework before calling `rockcraft init` or `charmcraft init`.
- Confirm the app is a web application by inspecting source code, not by asking.
- If the repo clearly separates frontend and backend, target the backend
  subdirectory automatically and note the decision.
- If frontend/static-asset build behavior is ambiguous, inspect directory
  structure and commit to a decision: separate directory → `separate-deployment`;
  same runtime → `embedded-in-backend-image`.
- Accept experimental extensions automatically and note the acceptance in output.
- Default additional relations to `optional: true` unless the app clearly
  cannot start without that dependency.
- Treat database migrations as a supported 12-factor path. Always infer
  the migration mode from repo signals; never leave it blank.
- Treat extra `-worker` and `-scheduler` services as supported when found
  alongside a main web service. Infer commands from repo evidence only.
- Deployment context (registry, Kubernetes cluster, Juju controller) is handled
  by the deploy stage — do not ask about or attempt to resolve these.
- Treat unsupported or inconsistent upstream paths as stop conditions with clear
  error output, not invitations to improvise.

## Stop Early

Stop immediately and output a clear error if any of these are true:

- the framework is outside the supported set (Flask, Django, FastAPI, ExpressJS, Go, Spring Boot)
- no web entrypoint can be found after thorough inspection
- the app cannot reasonably read runtime configuration from env vars
- the project only works after leaving the extension boundary

Use `references/known-risks.md` for framework-specific inconsistencies that
must be called out in the verdict output.

## Handoff Contract

If the project fits, write the handoff payload. Later skills consume this
directly — the payload must be complete and require no follow-up questions.

```yaml
framework: <string>
repo_path: <absolute path>
relations:
  - name: <relation name>
    optional: true | false
config_options_needed:
  - <option name>
frontend_build: none | embedded-in-backend-image | separate-deployment
migrations:
  mode: none | framework-managed | migrate-sh
  tool: <string or null>
background_services:
  workers:
    - <service name or command>
  schedulers:
    - <service name or command>
experimental_extensions_accepted: true
minimal_change_policy: true
ingress:
  needed: true
  external_hostname: null
```
