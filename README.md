# zorin-app

Flask + MongoDB user registry with a full **CI/CD → GitOps** deploy pipeline to GKE.

## Architecture

```
GitHub push (main)
│
├─► CI (pipeline.yaml)
│     lint → test → security-scan → docker build → Trivy → push Artifact Registry
│
├─► Deploy (deploy.yaml, on CI success)
│     GCP WIF auth → bump image tag in zorin-gitops repo (Helm values.yaml)
│
└─► ArgoCD detects drift → canary rollout to GKE (10→30→60→100%)
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, Flask 3.1, Gunicorn |
| DB | MongoDB (PyMongo 4.18) |
| Metrics | Prometheus (prometheus-flask-exporter) |
| Container | Multi-stage Docker (builder → runtime, non-root) |
| CI/CD | GitHub Actions → Artifact Registry → GitOps repo → Helm |
| Auth (CI) | GCP Workload Identity Federation (no long-lived keys) |
| Security | Trivy image scan, Bandit, pip-audit, Ruff |
| Orchestration | GKE + ArgoCD + Argo Rollouts |

## Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Render user list (supports `?limit=&after=` pagination) |
| `/add` | POST | Insert user (JSON: `{name, age}`) |
| `/health` | GET | DB ping → 200 / 503 |
| `/metrics` | GET | Prometheus scrape target |

## CI/CD Pipeline

| Job | Trigger | Actions |
|-----|---------|---------|
| `lint` | push + PR | Ruff |
| `test` | push + PR | pytest (all DB calls mocked) |
| `security-scan` | push + PR | pip-audit + Bandit |
| `build` | push only | Docker build → Trivy (CRITICAL blocks) → push to Artifact Registry |
| `deploy` | workflow_run (CI success) | WIF auth → yq tag bump → git push to `zorin-gitops` |

**No direct `kubectl`/`helm upgrade` from CI.** Deployment is purely declarative via GitOps.

## Key Design Decisions

- **Multi-stage Docker** — build deps (gcc, build-essential) never ship in the runtime image. Final image runs as `appuser` (non-root).
- **WIF for GCP** — zero long-lived credentials in GitHub secrets. Service account bound via `principalSet` scoped to `repo:org/repo`.
- **Health check in Dockerfile** — `HEALTHCHECK` hits `/health` which pings MongoDB; GKE detects DB loss.
- **Validation at the edge** — name length, age range, type coercion all rejected with 400 before touching the DB.
- **Canary via Argo Rollouts** — prod uses 10→30→60→100% weight steps with 5m pauses.
- **Immutable image tags** — every build is tagged with `github.sha`; no `latest` in prod.

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
├── app.py                  # Flask app (routes, validation, DB layer)
├── conftest.py             
├── templates/index.html    
├── tests/test_app.py       # Unit tests
├── Dockerfile              # Multi-stage (builder → runtime)
├── requirements.txt
├── .dockerignore
└── .github/workflows/
    ├── pipeline.yaml       # CI: lint, test, scan, build, push
    └── deploy.yaml         # GitOps: bump tag in values.yaml
```
