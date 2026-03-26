# Deployment Guide — Duke Schedule Solver

## Overview

Single **AWS EC2** instance running everything: nginx serves the frontend static files and proxies API requests to a Dockerized FastAPI backend.

| Component | Details |
|-----------|---------|
| **Instance** | `i-0dfeeeee71a452c9d` — `t3.small`, Ubuntu 22.04 |
| **Elastic IP** | `52.205.23.123` (static, persists across restarts) |
| **Domain** | `dukesolver.philliplin.dev` |
| **Frontend** | `https://dukesolver.philliplin.dev` (nginx with SSL) |
| **Backend API** | Docker container on port 8000, proxied by nginx |
| **SSL Certificate** | Let's Encrypt (auto-renews via certbot) |
| **Key pair** | `duke-solver-key` (local: `~/.ssh/id_ed25519`) |
| **Security group** | `sg-0a02026a8cc6307a9` — ports 22, 80, 443, 8000 |

---

## How to Update

### Update Backend Code

From your local machine:

```bash
# 1. Sync code changes to EC2
rsync -avz --progress \
  --exclude='.git' --exclude='node_modules' --exclude='frontend' \
  --exclude='DoodleCSS' --exclude='data' --exclude='__pycache__' \
  --exclude='dataslim/catalog.json' --exclude='dataslim/raw' \
  --exclude='dataslim/course_evaluations' --exclude='*.pdf' \
  --exclude='.vscode' --exclude='.claude' --exclude='QUICKSTART_WEBAPP_files' \
  -e "ssh -i ~/.ssh/id_ed25519" \
  ./ ubuntu@52.205.23.123:~/duke-schedule-solver/

# 2. Rebuild and restart the Docker container
ssh -i ~/.ssh/id_ed25519 ubuntu@52.205.23.123 "cd ~/duke-schedule-solver && \
  sudo docker build -t duke-solver-api . && \
  sudo docker stop duke-solver && sudo docker rm duke-solver && \
  sudo docker run -d --name duke-solver --restart unless-stopped \
    -p 8000:8000 -e ALLOWED_ORIGINS='*' -e UVICORN_WORKERS=2 \
    duke-solver-api"
```

### Update Frontend Code

```bash
# 1. Build the frontend with the production API URL
cd frontend
VITE_API_URL=https://dukesolver.philliplin.dev npx vite build

# 2. Upload the built files to EC2
rsync -avz --delete \
  -e "ssh -i ~/.ssh/id_ed25519" \
  dist/ \
  ubuntu@52.205.23.123:~/frontend-dist/
```

No nginx restart needed — it serves from `~/frontend-dist/` automatically.

### Update Data (New Semester / Pipeline Re-run)

```bash
# 1. Upload the new processed_courses.json and historical_catalog.json
scp -i ~/.ssh/id_ed25519 \
  dataslim/processed/processed_courses.json \
  ubuntu@52.205.23.123:~/duke-schedule-solver/dataslim/processed/
scp -i ~/.ssh/id_ed25519 \
  data/historical_catalog.json \
  ubuntu@52.205.23.123:~/duke-schedule-solver/data/

# 2. Rebuild and restart Docker (data is baked into the image)
ssh -i ~/.ssh/id_ed25519 ubuntu@52.205.23.123 "cd ~/duke-schedule-solver && \
  sudo docker build -t duke-solver-api . && \
  sudo docker stop duke-solver && sudo docker rm duke-solver && \
  sudo docker run -d --name duke-solver --restart unless-stopped \
    -p 8000:8000 -e ALLOWED_ORIGINS='https://dukesolver.philliplin.dev' -e UVICORN_WORKERS=2 \
    duke-solver-api"
```

---

## Troubleshooting

### Check if backend is running
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@52.205.23.123 "sudo docker ps"
```

### View backend logs
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@52.205.23.123 "sudo docker logs duke-solver --tail 50"
```

### Check nginx status
```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@52.205.23.123 "sudo systemctl status nginx"
```

### Test API health
```bash
curl https://dukesolver.philliplin.dev/
# Returns: {"status":"healthy","service":"Duke Schedule Solver API","version":"1.0.0"}
```

---

## Architecture Details

### Nginx Config (`/etc/nginx/sites-available/duke-solver`)

- SSL: Let's Encrypt certificate (auto-renews via certbot)
- HTTP -> HTTPS redirect automatic
- Serves static frontend from `/home/ubuntu/frontend-dist/`
- SPA fallback: all non-file routes -> `index.html`
- Proxies `/parse-transcript`, `/search-courses`, `/solve` -> `localhost:8000`
- `client_max_body_size 10M` for transcript PDF uploads
- `proxy_read_timeout 60s` on `/solve` for long solver runs

### Docker Container

- Image: `duke-solver-api` (Python 3.10-slim + OR-Tools + FastAPI)
- `PYTHONPATH=/app/backend:/app` for module resolution
- `UVICORN_WORKERS=2` (2 concurrent solver requests)
- `--restart unless-stopped` for auto-recovery

### Environment Variables

| Variable | Where | Default | Description |
|----------|-------|---------|-------------|
| `VITE_API_URL` | Frontend build | `http://localhost:8000` | Backend API URL (baked at build time) |
| `ALLOWED_ORIGINS` | Docker container | `http://localhost:5173` | CORS allowed origins (comma-separated) |
| `UVICORN_WORKERS` | Docker container | `2` | Number of API worker processes |
| `ANALYTICS_BUCKET` | Docker container | _(unset = no-op)_ | S3 bucket for analytics events |

---

## SSL Certificate Renewal

SSL certificates auto-renew via certbot timer:
```bash
# Check renewal timer status
ssh -i ~/.ssh/id_ed25519 ubuntu@52.205.23.123 "sudo systemctl status certbot.timer"

# Test renewal (dry run)
ssh -i ~/.ssh/id_ed25519 ubuntu@52.205.23.123 "sudo certbot renew --dry-run"
```
