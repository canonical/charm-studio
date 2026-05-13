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

Inspect first. Generate nothing until the fit verdict is clear.

## Skill Order

- Run this skill first.
- Hand off to `$12factor-rock` and `$12factor-charm` only after the fit verdict
  is explicit.
- Hand off to `$12factor-juju-terraform` last, after rock, charm, and target
  environment details are known.

## Workflow

1. Inspect the repository before asking questions.
2. Run `scripts/detect_framework.py <repo>` to get a framework verdict with signals.
3. If the repo clearly separates backend and frontend in a monorepo, stop treating the repo root as the packaging target. Confirm which backend subdirectory should be the 12-factor scope.
4. Confirm the detected framework with the user.
5. Confirm the application is meant to run as a web service on a Kubernetes-backed Juju model.
6. If the repo clearly separates backend and frontend in different subdirectories, default to applying the 12-factor workflow to the backend subdirectory only. Do not default to bundling both into one image.
7. If the repo has any frontend or static-asset build question, ask the user explicitly whether that build belongs inside the rock or remains a separate deployment concern. Do not infer `frontend_build` on your own.
8. Only consider a bundled frontend/backend image when the repo shape already behaves like one runtime application and the user explicitly accepts that exception path.
9. Ask the mandatory deployment-context questions from `references/question-bank.md`.
10. Confirm whether the app needs database migrations and whether they should be
   handled by framework-native tooling or a root `migrate.sh`.
11. Confirm whether the app needs extra `-worker` or `-scheduler` services
   alongside the main web service, and capture the intended commands.
12. If the user wants any relations declared in the charm beyond those already
   embedded in the charmcraft extension (ingress, grafana-dashboard,
   metrics-endpoint, and logging are extension-provided with fixed optionality),
   ask which of those additional relations should be optional in charm
   metadata. Do not infer requiredness from repo inspection or app behavior
   alone.
13. If the framework is FastAPI, Go, ExpressJS, or Spring Boot, ask whether the
   user accepts the current experimental extension path and edge-channel
   tooling requirement.
14. Once the user answers, run `scripts/preflight_targets.py` to verify the chosen Kubernetes context, Juju controller, registry, and required local tools.
15. Load `references/framework-detection.md` and `references/known-risks.md` before deciding whether to proceed.
16. Produce a fit verdict with:
   - detected framework
   - confirmed deployment context
   - structured handoff payload
   - required follow-up questions
   - explicit stop reasons if the project does not fit

## Non-Negotiables

- Detect the framework before calling `rockcraft init` or `charmcraft init`.
- Confirm the app is a web application.
- Confirm the deployment target is Kubernetes-backed.
- If the repo clearly separates frontend and backend, target the backend
  subdirectory for the 12-factor workflow.
- If frontend or static-asset build behavior is ambiguous, stop and ask the
  user whether that build belongs inside the rock or remains separate.
- Ask which registry, Kubernetes context, and Juju controller to use.
- Verify the chosen targets before build or deploy work.
- Ask before installing or changing tooling on the host.
- Surface experimental extension requirements before promising a supported path.
- If any relation beyond the extension-embedded set (ingress, grafana-dashboard,
  metrics-endpoint, logging) will be declared in the charm, ask whether it
  should be optional or required in charm metadata. Do not infer that yourself.
  Do not ask about extension-embedded relations — their optionality is fixed.
- Treat database migrations as a supported 12-factor path for every supported
  framework. Current `paas-charm` code checks `migrate`, then `migrate.sh`,
  then `migrate.py`, then `manage.py`, with the last match winning. For Spring
  Boot, prefer framework-managed migrations.
- Treat extra `-worker` and `-scheduler` services as supported when they sit
  alongside a main web service.
- Treat unsupported or inconsistent upstream paths as stop conditions, not invitations to improvise.

## Mandatory Questions

Ask these unless the answer is already explicit and reliable in the conversation:

- Which framework should I target?
- Is this application meant to run as a web service?
- Which Kubernetes context or cluster should I use?
- Which Juju controller and model should I use?
- Which OCI registry should hold the rock?
- Should the charm stay local, or is Charmhub publication in scope?
- If the repo separates frontend and backend, which subdirectory is the backend
  application root?
- If the app has a frontend or static-asset build step, should that build stay
  separate, or do you want it embedded into the backend image for this
  project?
- If `<framework>` is FastAPI, Go, ExpressJS, or Spring Boot: do you accept the
  current experimental extension path, including edge-channel tooling?
- Does the app need a database? If yes, should migrations stay
  framework-managed or should the rock expose a root `migrate.sh`?
- Does the app need extra `-worker` or `-scheduler` services alongside the
  main web service?
- Does the app need ingress, observability, Redis, RabbitMQ, S3, SMTP, OIDC,
  SAML, OpenFGA, tracing, or a proxy? (Note: ingress, grafana-dashboard,
  metrics-endpoint, and logging are already embedded in the charmcraft extension
  with fixed optionality — do not ask about those.)
- For each additional relation you want declared in the charm beyond the
  extension-embedded set, should it be optional or required in charm metadata?
- If ingress is needed: the skill will auto-detect the best ingress charm for
  the cluster and ask you to confirm when multiple options exist.

Use `references/question-bank.md` for the full grouped list.

## Stop Early

Stop and explain why if any of these are true:

- the framework is outside the supported set
- the project is not a web application
- the app cannot reasonably read runtime configuration from env vars
- the deployment target is not Kubernetes-backed Juju
- the user expects a pure Terraform-provider deployment for an unpublished local charm artifact
- the repo clearly separates frontend and backend and the requested scope is to
  force both into one image anyway
- the repo has a frontend/static build question and the user has not confirmed
  whether it should be embedded or kept separate
- a relation should be declared in the charm but the user has not confirmed
  whether it should be optional or required in charm metadata
- the project only works after leaving the extension boundary

Use `references/known-risks.md` for framework-specific inconsistencies that need explicit acknowledgement.

## Handoff Contract

If the project fits, hand off cleanly:

- to `$12factor-rock` with the confirmed framework, repo path, and rock deployment context
- to `$12factor-charm` with the confirmed framework, relation list plus explicit optionality, config needs, and minimal-change constraints
- to `$12factor-juju-terraform` with the chosen deployment mode and verified target environment

Use this minimum handoff shape so later skills do not guess:

```yaml
framework: <string>
repo_path: <absolute path>
k8s_context: <string>
kubectl_command: <string>
juju_controller: <string>
juju_model: <string or null>
registry: <string>
charm_publication: local | charmhub
deployment_mode: provider-first | hybrid-local-artifact
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
experimental_extensions_accepted: true | false
minimal_change_policy: true
ingress:
  needed: true | false
  external_hostname: <string or null>
```
