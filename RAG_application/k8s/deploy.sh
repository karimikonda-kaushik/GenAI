#!/usr/bin/env bash
# Build images into minikube Docker and deploy the RAG app.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop first."
  exit 1
fi

if ! minikube status >/dev/null 2>&1; then
  echo "minikube is not running. Run: minikube start --cpus=4 --memory=6144 --driver=docker"
  exit 1
fi

# Load API_KEY for frontend build
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${API_KEY:-}" ]]; then
  echo "API_KEY not set. Add it to .env before deploying."
  exit 1
fi

echo "==> Using minikube Docker daemon"
eval "$(minikube docker-env)"

echo "==> Building backend image (may take several minutes on first run)"
docker build -f Dockerfile.backend -t rag-backend:local .

echo "==> Building frontend image"
docker build -f Dockerfile.frontend \
  --build-arg "VITE_API_KEY=${API_KEY}" \
  -t rag-frontend:local .

echo "==> Creating Kubernetes secret from .env"
chmod +x k8s/create-secret.sh
./k8s/create-secret.sh

echo "==> Applying manifests"
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

echo ""
echo "==> Waiting for pods (backend first start downloads the embedding model — ~2–5 min)"
kubectl rollout status deployment/rag-backend --timeout=600s
kubectl rollout status deployment/rag-frontend --timeout=120s

echo ""
kubectl get pods,svc,ingress
echo ""
echo "Next steps:"
echo "  1. In a NEW terminal: minikube tunnel   (keep it running)"
echo "  2. Add to /etc/hosts:  $(minikube ip) rag.local"
echo "     Or: echo \"\$(minikube ip) rag.local\" | sudo tee -a /etc/hosts"
echo "  3. Open http://rag.local"
echo ""
echo "Health check (from another terminal):"
echo "  curl -H \"X-API-Key: \$API_KEY\" http://rag.local/api/health"
