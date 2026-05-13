---
name: 12factor-charm
description: >
  Creates or adapts a Canonical 12-factor charm in the supported `charm/`
  layout using Charmcraft and `paas-charm`. Preserves the stock generated charm
  by default, carries explicit relation optionality forward, mirrors required
  workload environment safely.
  WHEN: create charmcraft yaml, run charmcraft init,
  inspect paas-charm runtime, add confirmed relations, set relation optionality,
  mirror rock service environment, charm a 12-factor application
license: Apache-2.0
metadata:
  author: Canonical/platform-engineering
  version: "1.0.0"
  summary: Create a charm with relations and config options, then hand off packaging to the studio agent (also take care of env vars, rebuild the rock if needed).
  tags:
    - canonical
    - 12-factor
    - charmcraft
    - paas-charm
    - juju
---

# 12factor Charm

Always build the charm in `charm/`. Treat `paas-charm` as part of the contract.

## Skill Order

- Run `$12factor-fit` first when possible.
- Run this skill before `$12factor-juju-terraform`.
- This skill and `$12factor-rock` can proceed independently once the fit
  verdict and framework are confirmed.

## Workflow

1. Reuse the fit verdict from `$12factor-fit` if available. If not, confirm the framework and deployment context yourself.
2. Create or use a dedicated `charm/` subdirectory. Do not generate the charm at project root.
3. If the framework is FastAPI, Go, ExpressJS, or Spring Boot, auto-accept the
   experimental extension path. Ensure `charmcraft` is on an edge channel with
   `CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true` and proceed. Note the
   experimental acceptance in the output.
4. Run the exact profile from `references/framework-charm-contracts.md`, for
   example `charmcraft init --profile fastapi-framework --name <charm-name>`
   inside `charm/`. Always use this command to generate the charm — never copy
   from templates, previously generated files, or example charms.
5. Inspect the generated `charmcraft.yaml`, `requirements.txt`, and `src/charm.py`.
6. Load `references/framework-charm-contracts.md` and `references/paas-charm-runtime.md`.
7. Run `scripts/inspect_env_keys.py <repo> --framework <framework>` to
   inventory application env expectations before adding config or workload-side
   env bridges.
8. If the repo already has a `rockcraft.yaml`, inspect `services.*.environment`
   for the main app service and any confirmed worker or scheduler services.
   Assume those rock-defined env vars will not survive automatically once
   `paas-charm` renders the workload Pebble layer.
9. Add only user-confirmed relations and config options. Do not add relations
    that are already embedded in the charmcraft extension (ingress,
    grafana-dashboard, metrics-endpoint, logging) — those are already declared
    with fixed optionality and must not be re-declared or questioned.
10. If the optionality of a relation is not specified in the fit handoff, default
    to `optional: true`. Only set `optional: false` when the app clearly cannot
    start without that relation (e.g., a required database with no fallback).
    Never stop to ask the user about relation optionality.
11. For ExpressJS, verify whether the generated charm injects `app-port` while
   current `paas-charm` aliases still expect `port`. If so, add a
   non-conflicting `port` config option instead of rewriting charm logic.
12. Treat generated `paas-charm` env output as the baseline contract, not the
    whole workload contract. Any required env var defined in the rock service
    must also be re-established under charm control. Prefer non-conflicting
    charm config defaults for deploy-time values and a tiny workload-side
    defaulting bridge in the image, startup wrapper, or app entrypoint for
    static app-facing defaults before editing charm Python.
13. For built-in dynamic OAuth or OIDC config, prefer deploy-time config such as
    `<endpoint>-redirect-path` instead of charm subclassing or relation-hook
    overrides.
14. If live Juju or Pebble logs show service exit loops, CLI usage output, or
    `permission denied` on workload paths, treat that as a rock/runtime issue
    first and inspect the rock service command, runtime user, and writable
    paths before considering charm Python changes.
15. If `src/charm.py` changes are still necessary after exhausting viable
    workload-side adaptations, proceed with the change and include a clear note
    in the output explaining why no workload-side adaptation was viable.
16. If the app needs static-asset preparation or a frontend build, push that work
   back into the rock build instead of customizing charm runtime behavior.
17. Do not run `charmcraft pack` in this skill. Hand off packaging to the
    studio agent, which runs `charmcraft pack` after this skill completes.

## Extension-Embedded Relations

The charmcraft framework extensions already declare these relations in the
generated `charmcraft.yaml` with fixed optionality:

- **ingress** (interface: `ingress`) — required
- **grafana-dashboard** (interface: `grafana_dashboard`) — optional
- **metrics-endpoint** (interface: `prometheus_scrape`) — optional
- **logging** (interface: `loki_push_api`) — optional

Do not re-declare these in `charmcraft.yaml`. Do not ask the user whether they
want these relations or whether they should be optional — the extension owns
that decision. If the user mentions one of these, confirm it is already provided
by the extension and move on.

## Non-Negotiables

- Use `charm/`, not the app root.
- Always generate the charm via `charmcraft init --profile <framework> --name <charm-name>` inside `charm/`. Never copy from discovered templates, previously generated files, or example charms.
- Keep source changes minimal and justified.
- Keep `charmcraft.yaml` edits minimal.
- Add only relations that are confirmed in the fit handoff or inferred from the
  repo — do not add every possible relation.
- Do not re-declare or change the optionality of extension-embedded relations (ingress, grafana-dashboard, metrics-endpoint, logging).
- Set each declared relation's `optional` field from the fit handoff. If not
  specified in the handoff, default to `optional: true` unless the relation is
  clearly required (no-fallback database).
- Use secret-typed config for secrets where appropriate.
- Treat generated `paas-charm` behavior as the runtime truth.
- Treat generated `paas-charm` env output as the baseline contract.
- When `rockcraft.yaml` defines service env, mirror the required keys into the
  charm-managed workload too.
- Keep generated `src/charm.py` stock unless there is no viable workload-side
  adaptation; if charm.py must change, proceed and document the reason clearly.
- If you mention packaging commands, never suggest
  `charmcraft pack --destructive-mode`.

## Preferred Adaptations

- add non-conflicting charm config options for deployment-facing toggles
- mirror required rock-defined service env through non-conflicting charm config
  defaults when the values should stay operator-visible
- add a minimal workload-side env bridge or defaulting wrapper in the image,
  startup wrapper, or app entrypoint when `paas-charm` and the app use
  different names or when a static rock-defined env default must survive
- add a migration script only when the app needs one and the workflow supports it

## Avoid

- do not add every possible relation
- do not mark a declared relation non-optional by default unless the app
  clearly cannot start without it and the fit handoff confirms this
- do not collide with reserved framework config prefixes
- do not hard-code deployment-specific values into the app if a charm config option is the cleaner fit
- do not assume every framework uses the same env prefixes or metrics model
- do not assume `rockcraft.yaml` service `environment:` entries survive once
  `paas-charm` owns the workload Pebble layer
- do not treat Pebble restart failures caused by wrong service commands or
  unwritable workload paths as a default reason to edit `src/charm.py`
- do not override `_init_*` or `_on_*` relation methods just to rename env vars
  or tweak default values
- do not subclass the charm for built-in OAuth or OIDC relation behavior when
  deploy-time config already covers the requirement
- do not modify `src/charm.py` without documenting why a workload-side
  adaptation was not viable
- do not override private or semi-private `paas-charm` internals; if this is
  the only viable path, stop with a clear explanation of the risk rather than
  silently proceeding
- do not use `charmcraft pack --destructive-mode`

## Deployment Reminder

When deploying a local charm artifact later:

- use the full `.charm` filename
- keep the file in a Juju-accessible path, typically under the user home directory for snap-confined Juju

## Output Contract

Produce:

- a minimal `charmcraft.yaml`
- a `charm/` tree ready for `charmcraft pack` by the studio agent
- a clear config, secret, and relation contract for the deploy step, including
  relation optionality
