#!/bin/bash
# Stage 5: Run shadow search API for provider comparison.
#
# This script launches a secondary search API (port 18000) optionally with a
# different embedding provider and model, without disrupting the primary one.
#
# Usage:
#   ./scripts/run_shadow_search.sh --provider ollama --model nomic-embed-text
#   ./scripts/run_shadow_search.sh --stop   # stop shadow container
#   ./scripts/run_shadow_search.sh --query "dansk historie"  # one-off query
#
# Requirements: docker compose, existing modular base stack running (postgres).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOEGEMASKINE_DIR="${SCRIPT_DIR}/../soegemaskine"
cd "$SOEGEMASKINE_DIR"

PROVIDER_OVERRIDE=""
MODEL_OVERRIDE=""
RUN_QUERY=""
STOP_ONLY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --provider) PROVIDER_OVERRIDE="$2"; shift 2 ;;
    --model) MODEL_OVERRIDE="$2"; shift 2 ;;
    --query) RUN_QUERY="$2"; shift 2 ;;
    --stop) STOP_ONLY=true; shift ;;
    -h|--help)
      grep '^# ' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if $STOP_ONLY; then
  echo "Stopping shadow search..."
  docker compose -f docker-compose.base.yml -f docker-compose.shadow.yml down --remove-orphans || true
  exit 0
fi

if [ -n "$PROVIDER_OVERRIDE" ]; then
  case "$PROVIDER_OVERRIDE" in
    openai|ollama|dummy) :;;
    *) echo "Invalid provider: $PROVIDER_OVERRIDE"; exit 1 ;;
  esac
fi

echo "=== Shadow Search Startup ==="
echo "Provider override: ${PROVIDER_OVERRIDE:-'(none - inherits .env)'}"
echo "Model override:    ${MODEL_OVERRIDE:-'(none)'}"

ENV_INJECT=()
if [ -n "$PROVIDER_OVERRIDE" ]; then
  ENV_INJECT+=( -e PROVIDER="$PROVIDER_OVERRIDE" )
fi
if [ -n "$MODEL_OVERRIDE" ]; then
  if [ "$PROVIDER_OVERRIDE" = "openai" ]; then
    ENV_INJECT+=( -e OPENAI_MODEL="$MODEL_OVERRIDE" )
  elif [ "$PROVIDER_OVERRIDE" = "ollama" ]; then
    ENV_INJECT+=( -e OLLAMA_MODEL="$MODEL_OVERRIDE" )
  else
    ENV_INJECT+=( -e OPENAI_MODEL="$MODEL_OVERRIDE" -e OLLAMA_MODEL="$MODEL_OVERRIDE" )
  fi
fi

# Bring up shadow container (reuse running postgres and maybe primary search)
# We reuse the base file to ensure network/service references.

docker compose -f docker-compose.base.yml -f docker-compose.shadow.yml up -d postgres
# Launch shadow with overrides via run (ephemeral) or up (persistent). We'll use up for easier logs.
if [ ${#ENV_INJECT[@]} -gt 0 ]; then
  # Use run --no-deps to apply env overrides then replace container (remove previous if any)
  docker compose -f docker-compose.base.yml -f docker-compose.shadow.yml rm -f searchapi-shadow >/dev/null 2>&1 || true
  docker compose -f docker-compose.base.yml -f docker-compose.shadow.yml run -d --name dhosearch-shadow "${ENV_INJECT[@]}" searchapi-shadow
else
  docker compose -f docker-compose.base.yml -f docker-compose.shadow.yml up -d searchapi-shadow
fi

echo "Waiting for shadow API (port 18000)..."
for i in {1..20}; do
  if curl -sf http://localhost:18000/docs >/dev/null 2>&1; then
    echo "Shadow API ready."; break
  fi
  sleep 1
  if [ $i -eq 20 ]; then
    echo "Shadow API failed to become ready."; exit 1
  fi
done

if [ -n "$RUN_QUERY" ]; then
  echo "Executing one-off query: $RUN_QUERY" 
  curl -s -X POST http://localhost:18000/search -H 'Content-Type: application/json' -d '{"query": "'$RUN_QUERY'"}' | python3 -m json.tool || true
fi

echo "Use: docker logs -f dhosearch-shadow  (or stop with --stop)"
