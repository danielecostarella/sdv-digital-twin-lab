#!/usr/bin/env bash
# Downloads COVESA VSS JSON for the pinned version used by KUKSA Databroker.
# Run this once before `docker compose up`.

set -euo pipefail

VSS_VERSION="4.0"
DEST="services/databroker/vss/vss_release_4.0.json"

mkdir -p "$(dirname "${DEST}")"

echo "Downloading COVESA VSS ${VSS_VERSION}..."
curl -fL --retry 3 --retry-delay 2 \
  "https://github.com/COVESA/vehicle_signal_specification/releases/download/v${VSS_VERSION}/vss_rel_${VSS_VERSION}.json" \
  -o "${DEST}"

echo "VSS ${VSS_VERSION} saved to ${DEST}"
