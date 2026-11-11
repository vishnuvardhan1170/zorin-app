# zorin-app

Flask + MongoDB user registry with a full CI/CD → GitOps deploy pipeline to GKE.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, Flask 3.1, Gunicorn |
| DB | MongoDB (PyMongo 4.18) |
| Metrics | Prometheus (prometheus-flask-exporter) |
| Container | Multi-stage Docker (builder → runtime, non-root) |
| CI/CD | GitHub Actions → Artifact Registry → GitOps repo → Helm |
| Auth (CI) | GCP Workload Identity Federation (no long-lived keys) |
| Security | Trivy image scan, Bandit, pip-audit, Ruff |

## Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Render user list |
| `/add` | POST | Insert user |
| `/health` | GET | DB ping → 200 / 503 |
| `/metrics` | GET | Prometheus scrape target |

## Architecture
 

GitHub push (main)
→ CI: lint → test → security-scan → docker build → Trivy → push Artifact Registry
→ Deploy: update image tag in GitOps repo (Helm values.yaml)
→ ArgoCD / Argo Rollouts picks up change → canary rollout to GKE


- **CI** (`pipeline.yaml`): runs on push + PR. Build/push step only on push.
- **Deploy** (`deploy.yaml`): triggered by `workflow_run` (CI success on main). Uses GCP WIF to assume a service account scoped to the repo.
- **GitOps**: no direct `kubectl`/`helm upgrade` from CI. CI commits a tag bump to a separate `zorin-gitops` repo; ArgoCD handles the actual rollout.

## Key Design Decisions

- **Multi-stage Docker**: build deps (gcc) never ship in the runtime image. Final image runs as `appuser` (non-root).
- **WIF for GCP**: zero long-lived credentials in GitHub secrets. Service account bound via `principalSet` scoped to `repo:org/repo`.
- **Health check in Dockerfile**: `HEALTHCHECK` hits `/health` which pings MongoDB — GKE can detect DB loss.
- **Validation at the edge**: name length, age range, type coercion all rejected with 400 before touching the DB.
- **Canary via Argo Rollouts**: prod uses 10→30→60→100% weight steps with 5m pauses.

## Local Dev

```bash
pip install -r requirements.txt
# Start MongoDB locally (or set MONGO_URI)
export MONGO_URI=mongodb://localhost:27017/
python app.py          # http://127.0.0.1:8000
```

Tests
```bash
pytest -v
```

All DB calls are mocked (unittest.mock.patch). No MongoDB instance needed.

### Project Structure
```bash
├── app.py              # Flask app
├── templates/index.html
├── tests/test_app.py   # Unit tests
├── Dockerfile          # Multi-stage
├── requirements.txt
├── .github/workflows/
    ├── pipeline.yaml   # CI: lint, test, scan, build, push
    └── deploy.yaml     # GitOps: bump tag in values.yaml
```