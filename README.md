# zorin-app

Flask + MongoDB user registry with a full CI/CD → GitOps deploy pipeline to AWS EKS.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, Flask 3.1, Gunicorn |
| DB | MongoDB (PyMongo 4.18) |
| Metrics | Prometheus (prometheus-flask-exporter) |
| Container | Multi-stage Docker (builder → runtime, non-root) |
| CI/CD | GitHub Actions → ECR → GitOps repo → Helm |
| Auth (CI) | AWS OIDC (no long-lived keys) |
| Security | Trivy image scan, Bandit, pip-audit, Ruff |

## Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Render user list |
| `/add` | POST | Insert user |
| `/health` | GET | DB ping → 200 / 503 |
| `/metrics` | GET | Prometheus scrape target |

## Architecture

```
GitHub push (main)
  → CI: lint → test → security-scan → docker build → Trivy → push ECR
  → Deploy: update image tag in GitOps repo (Helm values.yaml)
  → ArgoCD / Helm picks up change → rolls out to EKS
```

- **CI** (`pipeline.yaml`): runs on push + PR. Build step only on push.
- **Deploy** (`deploy.yaml`): triggered by `workflow_run` (CI success on main). Uses OIDC to assume an IAM role scoped to `repo:…/zorin-app:ref:refs/heads/main`.
- **GitOps**: no direct `kubectl`/`helm upgrade` from CI. CI commits a tag bump to a separate `zorin-gitops` repo; a sync controller handles the actual rollout.

## Key Design Decisions

- **Multi-stage Docker**: build deps (gcc) never ship in the runtime image. Final image runs as `appuser` (non-root).
- **OIDC for AWS**: zero long-lived credentials in GitHub secrets. Role trust policy is scoped to the repo + branch.
- **Health check in Dockerfile**: `HEALTHCHECK` hits `/health` which pings MongoDB — orchestrator can detect DB loss.
- **Validation at the edge**: name length, age range, type coercion all rejected with 400 before touching the DB.

## Local Dev

```bash
pip install -r requirements.txt
# Start MongoDB locally (or set MONGO_URI)
export MONGO_URI=mongodb://localhost:27017/
python app.py          # http://127.0.0.1:8000
```

## Tests

```bash
pytest -v
```

All DB calls are mocked (`unittest.mock.patch`). No MongoDB instance needed.

## Project Structure

```
├── app.py              # Flask app
├── templates/index.html
├── tests/test_app.py   # Unit tests
├── Dockerfile          # Multi-stage
├── requirements.txt    
├── .github/workflows/
│   ├── pipeline.yaml   # CI: lint, test, scan, build, push
│   └── deploy.yaml     # GitOps: bump tag in values.yaml
└── IAM-trustpolicy     # OIDC role trust policy (reference)
```