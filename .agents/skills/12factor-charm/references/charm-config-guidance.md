# Charm Config Guidance

Prefer charm config over app rewrites when the issue is deployment-facing.

## Good Uses Of Charm Config

- runtime ports
- feature flags the app already knows how to read from env
- log-path or similar deployment-facing toggles
- secrets that should be represented as charm config or Juju secrets
- mirroring rock-defined service env that must stay visible at deploy time
  because `paas-charm` replaces the rock service layer

## Good Uses Of Small Source Changes

- small workload-side env bridges in a startup wrapper or app entrypoint when
  the app expects names different from fixed `paas-charm` output
- tiny workload-side defaulting wrappers when the rock used static service env
  that must still exist under charm management but does not justify new
  operator-facing config
- tiny migration entrypoints
- small layout shims only when the extension contract requires them

## Avoid

- broad application refactors
- colliding with reserved config prefixes such as `webserver-*` or framework-owned names
- adding relations the app does not truly need
- hiding framework-specific env differences behind generic wording
- assuming `rockcraft.yaml` service `environment:` survives unchanged once
  `paas-charm` renders the final workload layer
- editing `src/charm.py` just to rename env vars or change relation defaults
- editing `src/charm.py` just to restore rock-defined static env
- subclassing built-in OAuth or OIDC relation behavior when deploy-time config
  is sufficient
