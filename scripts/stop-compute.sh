#!/bin/bash
# Stop Compute / Cleanup Script (fail on errors; skip if instance missing or paused)
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

    echo "Checking Aura instance ${AURA_INSTANCE_ID} state"
    get_code=$(curl -sS -u "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" \
      "https://api.neo4j.io/v1/instances/${AURA_INSTANCE_ID}" \
      -H 'Accept: application/json' -o /tmp/aura_get.json -w "%{http_code}")
    echo "GET /instances/${AURA_INSTANCE_ID} code: $get_code"

    # Tenant-aware fallback for GET if 403 or 404 and AURA_TENANT_ID is provided
    if [[ "$get_code" -eq 403 || "$get_code" -eq 404 ]]; then
      if [[ -n "${AURA_TENANT_ID:-}" ]]; then
        echo "Retrying with tenant-aware endpoint: /tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID}"
        get_code=$(curl -sS -u "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" \
          "https://api.neo4j.io/v1/tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID}" \
          -H 'Accept: application/json' -o /tmp/aura_get.json -w "%{http_code}")
        echo "GET /tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID} code: $get_code"
      fi
    fi

    if [[ "$get_code" -eq 404 ]]; then
      echo "Aura instance not found; skipping"
      exit 0
    elif [[ "$get_code" -lt 200 || "$get_code" -ge 300 ]]; then
      echo "Failed to query Aura instance (HTTP $get_code)"
      sed 's/^/    /' /tmp/aura_get.json || true
      exit 1
    fi

    state=$(python3 - << 'PY'
import json
try:
  d=json.load(open("/tmp/aura_get.json"))
  print((d.get("state") or d.get("status") or "").lower())
except Exception:
  print("")
PY
)
    if [[ "$state" == "paused" ]]; then
      echo "Aura instance is already paused; skipping"
      exit 0
    fi

    echo "Attempting Aura pause for ${AURA_INSTANCE_ID}"
    post_code=$(curl -sS -u "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" -X POST \
      "https://api.neo4j.io/v1/instances/${AURA_INSTANCE_ID}/pause" \
      -H 'Content-Type: application/json' -d '{}' -o /tmp/aura_pause.json -w "%{http_code}")
    echo "POST /instances/${AURA_INSTANCE_ID}/pause code: $post_code"

    # Tenant-aware fallback for POST if 403 or 404 and AURA_TENANT_ID is provided
    if [[ "$post_code" -eq 403 || "$post_code" -eq 404 ]]; then
      if [[ -n "${AURA_TENANT_ID:-}" ]]; then
        echo "Retrying with tenant-aware endpoint: /tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID}/pause"
        post_code=$(curl -sS -u "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" -X POST \
          "https://api.neo4j.io/v1/tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID}/pause" \
          -H 'Content-Type: application/json' -d '{}' -o /tmp/aura_pause.json -w "%{http_code}")
        echo "POST /tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID}/pause code: $post_code"
      fi
    fi

    if [[ "$post_code" -eq 409 ]]; then
      echo "Aura instance already paused; skipping"
      exit 0
    elif [[ "$post_code" -lt 200 || "$post_code" -ge 300 ]]; then
      echo "Aura pause failed (HTTP $post_code)"
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
