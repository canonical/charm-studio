#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Running concierge prepare..."
sudo concierge prepare -c "${SCRIPT_DIR}/concierge.yaml"

echo "==> Adding k8s cloud to Juju client..."
sudo k8s config > /tmp/ck8s-config.yaml
if juju clouds --client 2>/dev/null | grep -q "^ck8s"; then
    juju update-k8s ck8s --client < /tmp/ck8s-config.yaml
else
    juju add-k8s ck8s --client < /tmp/ck8s-config.yaml
fi
rm -f /tmp/ck8s-config.yaml

echo "==> Adding ck8s cloud to the concierge-lxd controller..."
CONTROLLER=$(juju controllers --format=json 2>/dev/null | python3 -c "
import json,sys
d = json.load(sys.stdin)
# prefer concierge-lxd, else first controller
controllers = d.get('controllers', {})
print(next((k for k in controllers if 'lxd' in k), next(iter(controllers), 'concierge-lxd')))
")
echo "    Using controller: ${CONTROLLER}"
if juju clouds --controller "${CONTROLLER}" 2>/dev/null | grep -q "^ck8s"; then
    echo "    ck8s already registered on controller, skipping."
else
    juju add-cloud ck8s --controller "${CONTROLLER}"
fi

echo "==> Setting up haproxy model on ${CONTROLLER}..."
if juju models --controller "${CONTROLLER}" --format=json 2>/dev/null | python3 -c "import json,sys; models=[m['short-name'] for m in json.load(sys.stdin).get('models',[])]; exit(0 if 'haproxy' in models else 1)" 2>/dev/null; then
    echo "    Model 'haproxy' already exists, skipping add-model."
else
    juju add-model haproxy localhost/localhost --controller "${CONTROLLER}"
fi

if juju status -m "${CONTROLLER}:haproxy" --format=json 2>/dev/null | python3 -c "import json,sys; exit(0 if 'haproxy' in json.load(sys.stdin).get('applications',{}) else 1)" 2>/dev/null; then
    echo "    haproxy already deployed, skipping."
else
    juju deploy haproxy --channel 2.8/stable -m "${CONTROLLER}:haproxy"
    echo "    Waiting for haproxy to be ready..."
    juju wait-for application haproxy -m "${CONTROLLER}:haproxy" --timeout 10m
fi

echo "==> Done. haproxy deployed and ck8s cloud available on '${CONTROLLER}'."

echo "==> Setting up lego (OVH DNS-01) in haproxy model..."
# Source OVH credentials from .bashrc (OVH_ENDPOINT, OVH_APPLICATION_KEY,
# OVH_APPLICATION_SECRET, OVH_CONSUMER_KEY must be set there).
# Use grep+eval to extract exports since .bashrc guards against non-interactive shells.
eval "$(grep -E '^export OVH_' "${HOME}/.bashrc")"

: "${OVH_ENDPOINT:?OVH_ENDPOINT not set in ~/.bashrc}"
: "${OVH_APPLICATION_KEY:?OVH_APPLICATION_KEY not set in ~/.bashrc}"
: "${OVH_APPLICATION_SECRET:?OVH_APPLICATION_SECRET not set in ~/.bashrc}"
: "${OVH_CONSUMER_KEY:?OVH_CONSUMER_KEY not set in ~/.bashrc}"

# lego expects short endpoint names (ovh-eu / ovh-ca), translate full URLs.
case "${OVH_ENDPOINT}" in
    *eu.api.ovh.com*)  LEGO_OVH_ENDPOINT="ovh-eu" ;;
    *ca.api.ovh.com*)  LEGO_OVH_ENDPOINT="ovh-ca" ;;
    *us.api.ovh.com*)  LEGO_OVH_ENDPOINT="ovh-us" ;;
    *)                 LEGO_OVH_ENDPOINT="${OVH_ENDPOINT}" ;;
esac

# Create or update the Juju secret holding OVH credentials.
LEGO_SECRET_NAME="ovh-lego-credentials"
if juju secrets -m "${CONTROLLER}:haproxy" 2>/dev/null | awk 'NR>1 {print $2}' | grep -qx "${LEGO_SECRET_NAME}"; then
    echo "    Juju secret '${LEGO_SECRET_NAME}' already exists, updating..."
    SECRET_ID=$(juju secrets -m "${CONTROLLER}:haproxy" 2>/dev/null | awk -v name="${LEGO_SECRET_NAME}" 'NR>1 && $2==name {print $1}')
    juju update-secret "${SECRET_ID}" -m "${CONTROLLER}:haproxy" \
        ovh-endpoint="${LEGO_OVH_ENDPOINT}" \
        ovh-application-key="${OVH_APPLICATION_KEY}" \
        ovh-application-secret="${OVH_APPLICATION_SECRET}" \
        ovh-consumer-key="${OVH_CONSUMER_KEY}"
else
    echo "    Creating Juju secret '${LEGO_SECRET_NAME}'..."
    SECRET_ID=$(juju add-secret "${LEGO_SECRET_NAME}" -m "${CONTROLLER}:haproxy" \
        ovh-endpoint="${LEGO_OVH_ENDPOINT}" \
        ovh-application-key="${OVH_APPLICATION_KEY}" \
        ovh-application-secret="${OVH_APPLICATION_SECRET}" \
        ovh-consumer-key="${OVH_CONSUMER_KEY}" \
        | awk '{print $NF}')
fi

# Deploy lego if not already present.
if juju status -m "${CONTROLLER}:haproxy" --format=json 2>/dev/null | python3 -c "import json,sys; exit(0 if 'lego' in json.load(sys.stdin).get('applications',{}) else 1)" 2>/dev/null; then
    echo "    lego already deployed, skipping."
else
    juju deploy lego -m "${CONTROLLER}:haproxy" \
        --config plugin=ovh \
        --config email=admin@charmhub.studio \
        --config plugin-config-secret-id="${SECRET_ID}"
    juju grant-secret "${SECRET_ID}" lego -m "${CONTROLLER}:haproxy"
    echo "    Waiting for lego to be ready..."
    juju wait-for application lego -m "${CONTROLLER}:haproxy" --timeout 5m
fi

echo "==> Integrating lego with haproxy (tls-certificates)..."
if juju status -m "${CONTROLLER}:haproxy" --relations 2>/dev/null | grep -q "lego.*haproxy\|haproxy.*lego"; then
    echo "    lego:certificates <-> haproxy:certificates already integrated, skipping."
else
    juju integrate lego:certificates haproxy:certificates -m "${CONTROLLER}:haproxy"
fi

echo "==> Creating cross-model offer for haproxy-route..."
if juju offers -m "${CONTROLLER}:haproxy" --application haproxy 2>/dev/null | grep -q "haproxy-route"; then
    echo "    Offer 'haproxy-route' already exists, skipping."
else
    juju offer -c "${CONTROLLER}" haproxy.haproxy:haproxy-route
fi

echo "==> Done. lego deployed with OVH DNS-01 in '${CONTROLLER}:haproxy'."

echo "==> Applying registry config to k8s cluster..."
curl -fsSL https://raw.githubusercontent.com/canonical/spring-petclinic/refs/heads/resources/registry.yaml | kubectl apply -f -
echo "==> Done."
