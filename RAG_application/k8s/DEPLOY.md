# Kubernetes deployment (minikube)

## Prerequisites

- Docker Desktop running
- minikube cluster: `minikube start --cpus=4 --memory=6144 --driver=docker`
- Ingress addon: `minikube addons enable ingress`
- `.env` filled in (copy from `.env.example`), especially:
  - `GOOGLE_API_KEY`
  - `DATABASE_URL` (Supabase)
  - `API_KEY` (generate: `openssl rand -hex 32`)
  - `REQUIRE_AUTH=true`

Apply DB migrations on Supabase before first deploy:

- `database/schema.sql`
- `database/migrations/001_hybrid_fts.sql`
- `database/migrations/002_user_auth.sql`

## One-command deploy

```bash
cd RAG_application
chmod +x k8s/deploy.sh k8s/create-secret.sh
./k8s/deploy.sh
```

## Manual steps

```bash
cd RAG_application
eval $(minikube docker-env)

docker build -f Dockerfile.backend -t rag-backend:local .
docker build -f Dockerfile.frontend \
  --build-arg VITE_API_KEY="$(grep ^API_KEY= .env | cut -d= -f2-)" \
  -t rag-frontend:local .

./k8s/create-secret.sh
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

## Access the app

**Terminal 1** — keep running:

```bash
minikube tunnel
```

**Terminal 2** — hosts entry (once):

```bash
echo "$(minikube ip) rag.local" | sudo tee -a /etc/hosts
```

Open **http://rag.local**

## Verify

```bash
kubectl get pods
kubectl logs -f deployment/rag-backend

# Health (replace with your API_KEY)
curl -H "X-API-Key: YOUR_API_KEY" http://rag.local/api/health
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ImagePullBackOff` | Run `eval $(minikube docker-env)` then rebuild images |
| Backend `CrashLoopBackOff` | Check logs; often `DATABASE_URL` or missing migration |
| Slow first start | Normal — downloads `sentence-transformers` model (~80MB) |
| 401 on API | `VITE_API_KEY` in frontend build must match backend `API_KEY` |
| Can't reach rag.local | Ensure `minikube tunnel` is running |

## Cloud cluster (GKE / EKS / AKS)

1. Push images to a registry (remove `imagePullPolicy: Never`)
2. Store secrets in the cloud secret manager or `kubectl create secret`
3. Set `CORS_ORIGINS` in `configmap.yaml` to your real domain
4. Add TLS via cert-manager + Ingress annotations
