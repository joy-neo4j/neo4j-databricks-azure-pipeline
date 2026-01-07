#!/bin/bash
# Stop Compute / Cleanup Script (OAuth2 Bearer; strict 202)
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

    echo "Requesting OAuth2 access token"
    token_resp=$(curl -sS --request POST 'https://api.neo4j.io/oauth/token' \
      --user "$AURA_CLIENT_ID:$AURA_CLIENT_SECRET" \
      --header 'Content-Type: application/x-www-form-urlencoded' \
      --data-urlencode 'grant_type=client_credentials')
    ACCESS_TOKEN=$(echo "$token_resp" | jq -r '.access_token')
    if [[ -z "${ACCESS_TOKEN}" || "${ACCESS_TOKEN}" == "null" ]]; then
      echo "Failed to obtain access token"
      echo "$token_resp" | sed 's/^/    /'
      exit 1
    fi
    echo "✅ Access token acquired"

    base="https://api.neo4j.io/v1"
    inst_pause="${base}/instances/${AURA_INSTANCE_ID}/pause"
    ten_pause="${base}/tenants/${AURA_TENANT_ID}/instances/${AURA_INSTANCE_ID}/pause"

    echo "Attempting Aura pause: ${inst_pause}"
    code=$(curl -sS -X POST \
      "$inst_pause" -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H 'Content-Type: application/json' -d '{}' \
      -o /tmp/aura_pause.json -w "%{http_code}") || code=0
    echo "POST $inst_pause code: $code"

    if [[ ( "$code" -eq 403 || "$code" -eq 404 ) && -n "${AURA_TENANT_ID:-}" ]]; then
      echo "Retrying with tenant endpoint: ${ten_pause}"
      code=$(curl -sS -X POST \
        "$ten_pause" -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H 'Content-Type: application/json' -d '{}' \
        -o /tmp/aura_pause.json -w "%{http_code}") || code=0
      echo "POST $ten_pause code: $code"
    fi

    # Strict success: only 202 is accepted
    if [[ "$code" -ne 202 ]]; then
      echo "Aura pause failed (HTTP $code). Only 202 is accepted as success."
      sed 's/^/    /' /tmp/aura_pause.json || true
      exit 1
    fi

    echo "✅ Aura pause request accepted (202)"
    ;;
  cleanup-temp)
    echo "Cleaning up temporary data... (add steps as needed)"
    ;;
  *)
    echo "Unknown action: ${ACTION}"; exit 1;;

esac
