# Deployment Guide — Duke Schedule Solver

## Overview

Single **AWS EC2** instance running everything: nginx serves the frontend static files and proxies API requests to a Dockerized FastAPI backend.

| Component | Details |
|-----------|---------|
| **Instance** | `<YOUR_INSTANCE_ID>` — `t3.small`, Ubuntu 22.04 |
| **Elastic IP** | `<YOUR_ELASTIC_IP>` (static, persists across restarts) |
| **Domain** | `<YOUR_DOMAIN>` |
| **Frontend** | `https://<YOUR_DOMAIN>` (nginx with SSL) |
| **Backend API** | Docker container on port 8000, proxied by nginx |
| **SSL Certificate** | Let's Encrypt (auto-renews via certbot) |
| **Key pair** | `<YOUR_KEY_NAME>` (local: `<YOUR_KEY_PATH>`) |
| **Security group** | `<YOUR_SECURITY_GROUP>` — ports 22, 80, 443, 8000 |

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
  -e "ssh -i <YOUR_KEY_PATH>" \
  ./ ubuntu@<YOUR_ELASTIC_IP>:~/duke-schedule-solver/

# 2. Rebuild and restart the Docker container
ssh -i <YOUR_KEY_PATH> ubuntu@<YOUR_ELASTIC_IP> "cd ~/duke-schedule-solver && \
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
VITE_API_URL=https://<YOUR_DOMAIN> npx vite build

# 2. Upload the built files to EC2
rsync -avz --delete \
  -e "ssh -i <YOUR_KEY_PATH>" \
  dist/ \
  ubuntu@<YOUR_ELASTIC_IP>:~/frontend-dist/
```

No nginx restart needed — it serves from `~/frontend-dist/` automatically.

### Update Data (New Semester / Pipeline Re-run)

```bash
# 1. Upload the new processed_courses.json
scp -i <YOUR_KEY_PATH> \
  dataslim/processed/processed_courses.json \
  ubuntu@<YOUR_ELASTIC_IP>:~/duke-schedule-solver/dataslim/processed/

# 2. Rebuild and restart Docker (data is baked into the image)
ssh -i <YOUR_KEY_PATH> ubuntu@<YOUR_ELASTIC_IP> "cd ~/duke-schedule-solver && \
  sudo docker build -t duke-solver-api . && \
  sudo docker stop duke-solver && sudo docker rm duke-solver && \
  sudo docker run -d --name duke-solver --restart unless-stopped \
    -p 8000:8000 -e ALLOWED_ORIGINS='*' -e UVICORN_WORKERS=2 \
    duke-solver-api"
```

---

## Troubleshooting

### Check if backend is running
```bash
ssh -i <YOUR_KEY_PATH> ubuntu@<YOUR_ELASTIC_IP> "sudo docker ps"
```

### View backend logs
```bash
ssh -i <YOUR_KEY_PATH> ubuntu@<YOUR_ELASTIC_IP> "sudo docker logs duke-solver --tail 50"
```

### Check nginx status
```bash
ssh -i <YOUR_KEY_PATH> ubuntu@<YOUR_ELASTIC_IP> "sudo systemctl status nginx"
```

### Test API health
```bash
curl https://<YOUR_DOMAIN>/
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
| `ALLOWED_ORIGINS` | Docker container | `*` | CORS allowed origins (comma-separated) |
| `UVICORN_WORKERS` | Docker container | `2` | Number of API worker processes |
| `ANALYTICS_BUCKET` | Docker container | _(unset = no-op)_ | S3 bucket for analytics events |

---

## SSL Certificate Renewal

SSL certificates auto-renew via certbot timer:
```bash
# Check renewal timer status
ssh -i <YOUR_KEY_PATH> ubuntu@<YOUR_ELASTIC_IP> "sudo systemctl status certbot.timer"

# Test renewal (dry run)
ssh -i <YOUR_KEY_PATH> ubuntu@<YOUR_ELASTIC_IP> "sudo certbot renew --dry-run"
```
