#!/usr/bin/env bash
# Create rag-secrets from RAG_application/.env (never commit secret.yaml)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env"
OUT="${ROOT}/k8s/secret.yaml"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy .env.example and fill in values."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${GOOGLE_API_KEY:?GOOGLE_API_KEY not set in .env}"
: "${DATABASE_URL:?DATABASE_URL not set in .env}"
: "${API_KEY:?API_KEY not set in .env}"

SUPABASE_JWT_SECRET="${SUPABASE_JWT_SECRET:-}"

cat > "$OUT" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
  labels:
    app: rag-app
type: Opaque
stringData:
  GOOGLE_API_KEY: "${GOOGLE_API_KEY}"
  DATABASE_URL: "${DATABASE_URL}"
  API_KEY: "${API_KEY}"
  SUPABASE_JWT_SECRET: "${SUPABASE_JWT_SECRET}"
EOF

echo "Wrote $OUT (gitignored — do not commit)"
