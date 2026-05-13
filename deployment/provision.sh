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

echo "==> Done. k8s cloud 'ck8s' is available on the '${CONTROLLER}' controller."
