```markdown
# zorin-app

Flask + MongoDB user registry. Dockerized, CI/CD via GitHub Actions → ECR → GitOps (Helm).

## Stack

| Layer | Tech |
|---|---|
| App | Flask, Gunicorn |
| DB | MongoDB |
| Metrics | prometheus-flask-exporter → `/metrics` |
| Container | python:3.11, multi-stage |
| Auth | AWS OIDC (no long-lived keys) |

## Local dev

```bash
# Requires MongoDB on localhost:27017
pip install -r requirements.txt
python app.py          # http://127.0.0.1:8000
```

No `MONGO_URI` needed locally (falls back to `mongodb://localhost:27017/`). In production (`FLASK_ENV=production`) the app **refuses to start** without it.

## Docker

```bash
docker build -t zorin-app .
docker run -e MONGO_URI=mongodb://host:27017/ -p 8000:8000 zorin-app
```

Healthcheck: `GET /health` every 30 s.

## Tests

```bash
pip install pytest
pytest -v
```


## CI/CD

```
push/PR → CI (lint, test, security-scan, build, trivy, push to ECR)
       → Deploy (on CI success: update helm/values.yaml in gitops repo)
```

**Prerequisites (one-time, AWS side):**

1. OIDC provider: `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`
2. IAM role `github-actions-ecr-push` with the trust policy in `IAM-trustpolicy` (replace `YOUR_AWS_ACCOUNT_ID`)
3. ECR permissions on that role
4. Repo secret: `GITOPS_TOKEN` (PAT with write access to `vishnuvardhan1170/zorin-gitops`)

