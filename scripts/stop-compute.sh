#!/bin/bash
# Stop Compute / Cleanup Script (best-effort tenant-aware pause)
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
    base="https://api.neo4j.io/v1"
    inst_pause="${base}/instances/${AURA_INSTANCE_ID}/pause"
    ten_pause="${base}/tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID}/pause"

    echo "Attempting Aura pause: ${inst_pause}"
    code=$(curl -sS -u "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" -X POST \
      "$inst_pause" -H 'Content-Type: application/json' -d '{}' \
      -o /tmp/aura_pause.json -w "%{http_code}") || code=0
    echo "POST $inst_pause code: $code"

    if [[ ( "$code" -eq 403 || "$code" -eq 404 ) && -n "${AURA_TENANT_ID:-}" ]]; then
      echo "Retrying with tenant endpoint: ${ten_pause}"
      code=$(curl -sS -u "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" -X POST \
        "$ten_pause" -H 'Content-Type: application/json' -d '{}' \
        -o /tmp/aura_pause.json -w "%{http_code}") || code=0
      echo "POST $ten_pause code: $code"
    fi

    if [[ "$code" -eq 404 ]]; then
      echo "Aura instance not found; skipping"
      exit 0
    elif [[ "$code" -eq 409 ]]; then
      echo "Aura instance already paused; skipping"
      exit 0
    elif [[ "$code" -eq 403 ]]; then
      echo "Aura pause endpoint forbidden for this tenant/plan; skipping (best-effort)"
      sed 's/^/    /' /tmp/aura_pause.json || true
      exit 0
    elif [[ "$code" -lt 200 || "$code" -ge 300 ]]; then
      echo "Aura pause failed (HTTP $code)"
      sed 's/^/    /' /tmp/aura_pause.json || true
      exit 1
    fi

    echo "✅ Aura pause request accepted"
    ;;
  cleanup-temp)
    echo "Cleaning up temporary data... (add steps as needed)"
    ;;
  *)
    echo "Unknown action: ${ACTION}"; exit 1;;

esac
