#!/bin/bash
# Stop Compute / Cleanup Script (best-effort; fail on errors)
set -euo pipefail
ACTION=${1:-stop-dbx-clusters}

echo "🛑 Stop Compute action: ${ACTION}"
case "$ACTION" in
  stop-dbx-clusters)
    echo "Use the workflow job to stop clusters via Go CLI."
    ;;
  stop-aura)
    if [[ -z "${AURA_CLIENT_ID:-}" || -z "${AURA_CLIENT_SECRET:-}" || -z "${AURA_INSTANCE_ID:-}" ]]; then
      echo "Aura credentials or instance ID not provided; failing"
      exit 1
    fi
    echo "Attempting Aura suspend for ${AURA_INSTANCE_ID}"
    curl -sS -u "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" -X POST \
      "https://api.neo4j.io/v1/instances/${AURA_INSTANCE_ID}/suspend" \
      -H 'Content-Type: application/json' -d '{}' -o /tmp/aura_resp.txt -w "%{http_code}"
    ;;
  cleanup-temp)
    echo "Cleaning up temporary data... (add steps as needed)"
    ;;
  *)
    echo "Unknown action: ${ACTION}"; exit 1;;

esac
