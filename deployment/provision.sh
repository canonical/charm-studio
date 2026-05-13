#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Running concierge prepare..."
concierge prepare -c "${SCRIPT_DIR}/concierge.yaml"

echo "==> Adding k8s cloud to Juju client..."
sudo k8s config | juju add-k8s ck8s --client

echo "==> Adding ck8s cloud to the localhost controller..."
juju add-cloud ck8s --controller localhost

echo "==> Done. k8s cloud 'ck8s' is available on the 'localhost' controller."
