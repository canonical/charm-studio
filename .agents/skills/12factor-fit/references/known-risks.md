# Known Risks And Current Upstream Discrepancies

Treat these as implementation facts, not as noise.

## Hard Stop Conditions

- unsupported framework
- not a web application
- not a Kubernetes-backed Juju target
- app cannot reasonably consume runtime config from env vars
- deployment requires leaving the stock extension model
- user expects a pure Terraform-provider deployment for an unpublished local charm
- repo clearly separates frontend and backend, but the requested scope still
  tries to force both into one bundled image

## Current Upstream Discrepancies

### Flask And Django Charmcraft Base Mismatch

Current Charmcraft init templates emit `base: ubuntu@24.04`, while current
extension code still reports `ubuntu@22.04` support.

Behavior:

- do not hide the mismatch
- verify actual tool behavior when you are executing
- if the chosen environment or tool version makes it relevant, call it out

### ExpressJS Config Mismatch

Charmcraft’s ExpressJS extension injects `app-port`, while current
`paas-charm` ExpressJS config expects `port`. `paas-charm` also expects
`node-env`, which Charmcraft does not inject by default.

Behavior:

- call this out explicitly before promising a clean ExpressJS path
- verify the generated charm behavior during execution
- stop if the repo would require unsupported custom charm behavior to reconcile it

### Django Layout And Python-Plugin Friction

Current Django rock behavior is stricter than many realistic upstream repos:

- the extension expects the runtime app under `<repo>/<project-name>/`
- default discovery then expects either `<project-name>/wsgi.py` or
  `mysite/wsgi.py`
- the Craft Python plugin may also run `pip install .`, which can fail when a
  repo contains both `pyproject.toml` and the required `charm/` directory
- current `paas-charm` migration selection uses sequential checks, so the last
  present file wins: `migrate`, `migrate.sh`, `migrate.py`, then
  `manage.py migrate`
- in practice that means a normal Django repo with `manage.py` will not use a
  new `migrate.sh` unless `manage.py` is absent

Behavior:

- call out the layout expectation before promising a clean Django path
- prefer a small trial-copy layout adaptation over a manual rock
- if `pip install .` fails because of project metadata plus `charm/`, classify
  it as a build-tooling interaction, not an app-level defect
- treat migrations as supported, but do not add a Django `migrate.sh`
  expecting it to override `manage.py migrate`
- if the app needs `collectstatic` or a frontend build, prefer a rock-build fix
  before considering any charm customization

### Go Organize Rule

Current Go extension behavior is easy to break accidentally:

- the default service command and binary organize rule line up only when the
  built binary name matches the rock name
- overriding the service command disables the extension’s default binary
  organize behavior

Behavior:

- surface this before editing `services.go.command`
- if the binary name and rock name differ, prefer an explicit
  `go-framework/install-app.organize` mapping
- do not replace the extension with a manual rock just to route the binary

### FastAPI Bare-Base Python Version

FastAPI currently supports `base: bare`, where the Python interpreter comes
from `build-base`.

- `ubuntu@22.04` gives Python `3.10`
- `ubuntu@24.04` gives Python `3.12`

Behavior:

- treat interpreter choice as a first-class compatibility lever
- prefer an older supported `build-base` before upgrading app dependencies
- call this out early when the upstream app pins older FastAPI or Pydantic
  versions

## Infrastructure Noise To Ignore In Verdicts

Do not treat these as product lessons:

- temporary disk-pressure issues
- a broken local registry that the user can repair
- stale local controller or cluster state
- stale Kubernetes taints that survive after the real host-capacity issue is gone

Preflight them, but do not confuse them with framework fit.

## Monorepo Scope Rule

If a repository clearly separates frontend and backend into different
subdirectories, the default and recommended behavior is:

- apply the 12-factor skills to the backend subdirectory
- keep the frontend as a separate deployment concern

Do not treat that repo shape as a bundled-image candidate by default.
