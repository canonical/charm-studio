# Question Bank

Ask these unless the answer is already explicit and reliable.

## Fit And Intent

- Is `<framework>` the framework you want me to target?
- Is this application meant to run as a web service?
- Is the target Juju model Kubernetes-backed?
- If the repo is a monorepo, which subdirectory is the backend application root?
- Does the repo clearly separate frontend and backend into different subdirectories?
- If `<framework>` is FastAPI, Go, ExpressJS, or Spring Boot: do you accept the
  current experimental extension path, including edge-channel `rockcraft` and
  `charmcraft`?

## Deployment Contract

- Should the charm remain local, or do you want a Charmhub-first workflow?
- Do you want Terraform to manage only supported provider resources, with Juju CLI covering the local charm gap if needed?
- Which Juju controller should I use?
- Which model should I use or create?

## Rock And Registry

- Which OCI registry should hold the rock?
- Can the target cluster pull from that registry?
- Do registry credentials need to be configured?

## Cluster Selection

- Which Kubernetes context or cluster should I target?
- Should I inspect the available contexts before you choose?

## Runtime Behavior

- Which port should the application listen on?
- Which settings should become charm config options?
- Which of those settings are secrets?
- Does the app have a frontend build step such as webpack, Vite, Angular, Vue,
  `collectstatic`, or another static-asset build?
- Should that frontend or static-asset build stay separate, or do you want it
  embedded into the backend image for this project?
- If the repo clearly separates frontend and backend, should I scope the skill
  to the backend subdirectory and leave the frontend as a separate deployment?
- If there is a frontend build in an otherwise single-runtime app, are we
  intentionally embedding the built assets into the backend image for this
  project?
- Does the app require a database? If yes, which one?
- Are database migrations needed? If yes, should they stay framework-managed or
  should I add a root `migrate.sh` that delegates to the existing migration
  tool?
- Which migration tool does the app use, if any?
- Does the app need extra `-worker` or `-scheduler` services alongside the web
  service? If yes, what commands should they run?
- Do you need ingress, observability, proxying, S3, SMTP, Redis, RabbitMQ, OIDC, SAML, OpenFGA, or tracing now?
  (Note: ingress, grafana-dashboard, metrics-endpoint, and logging are already
  embedded in the charmcraft extension with fixed optionality — do not ask about
  those.)
- For each additional relation you want declared in the charm beyond the
  extension-embedded set, should it be optional or required in charm metadata?
- If ingress is needed, what external hostname should the app be reachable at?
  (The ingress charm will be auto-detected from the cluster; you will be asked
  to confirm if multiple options are available.)

## Layout Adaptation

- The `<framework>` extension expects the app under `<expected-path>/`. If your
  repo does not match, is a small trial-copy layout adaptation acceptable?
