# Deployment Guide — Ultimate Running Schedule

## Vereiste API Keys & Credentials

| Variabele | Service | Ophalen via |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude AI | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `GARMIN_ENCRYPTION_KEY` | Fernet (AES-256) | Zie genereren hieronder |
| `SECRET_KEY` | JWT signing | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL | Eigen database (zie stap 2) |

### Keys genereren
```bash
# JWT secret
openssl rand -hex 32

# Garmin Fernet encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Installatie op Debian 12 (Bookworm)

### 1. Systeemafhankelijkheden

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  python3.12 python3.12-venv python3-pip \
  postgresql postgresql-contrib \
  nginx certbot python3-certbot-nginx \
  nodejs npm git curl build-essential \
  libpq-dev libffi-dev
```

### 2. PostgreSQL opzetten

```bash
sudo systemctl enable --now postgresql

sudo -u postgres psql <<SQL
CREATE USER runuser WITH PASSWORD 'vervang_dit_wachtwoord';
CREATE DATABASE rundb OWNER runuser;
GRANT ALL PRIVILEGES ON DATABASE rundb TO runuser;
SQL
```

### 3. Applicatiegebruiker aanmaken

```bash
sudo useradd -m -s /bin/bash runapp
sudo su - runapp
```

### 4. Applicatie ophalen

```bash
# Als runapp:
git clone https://github.com/fhettinga/ultimate-running-schedule.git ~/app
cd ~/app
```

### 5. Backend installeren

```bash
cd ~/app/backend

# Virtuele omgeving
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Environment aanmaken
cp .env.example .env
nano .env
# ↑ Vul in:
#   DATABASE_URL=postgresql+asyncpg://runuser:JOUWPASS@localhost:5432/rundb
#   SECRET_KEY=<output van openssl rand -hex 32>
#   ANTHROPIC_API_KEY=sk-ant-...
#   GARMIN_ENCRYPTION_KEY=<output van Fernet.generate_key()>
#   ALLOWED_ORIGINS=https://jouwdomein.nl
#   APP_ENV=production

# Database migraties uitvoeren
alembic upgrade head
```

### 6. Frontend bouwen

```bash
cd ~/app/frontend
npm ci --frozen-lockfile

# Environment aanmaken
echo "NEXT_PUBLIC_API_URL=https://jouwdomein.nl/api/v1" > .env.local

# Productiebuild
npm run build
```

### 7. systemd services

**Backend** — `/etc/systemd/system/runai-backend.service`:

```ini
[Unit]
Description=RunAI Backend (FastAPI / Uvicorn)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=runapp
Group=runapp
WorkingDirectory=/home/runapp/app/backend
EnvironmentFile=/home/runapp/app/backend/.env
ExecStart=/home/runapp/app/backend/.venv/bin/uvicorn \
          app.main:app \
          --host 127.0.0.1 \
          --port 8000 \
          --workers 2 \
          --proxy-headers
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=runai-backend

[Install]
WantedBy=multi-user.target
```

**Frontend** — `/etc/systemd/system/runai-frontend.service`:

```ini
[Unit]
Description=RunAI Frontend (Next.js)
After=network.target runai-backend.service

[Service]
Type=exec
User=runapp
Group=runapp
WorkingDirectory=/home/runapp/app/frontend
Environment=NODE_ENV=production
Environment=PORT=3001
Environment=HOSTNAME=127.0.0.1
Environment=NEXT_PUBLIC_API_URL=https://jouwdomein.nl/api/v1
ExecStart=/usr/bin/node .next/standalone/server.js
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=runai-frontend

[Install]
WantedBy=multi-user.target
```

```bash
# Activeren en starten
sudo systemctl daemon-reload
sudo systemctl enable --now runai-backend runai-frontend

# Status controleren
sudo systemctl status runai-backend runai-frontend
```

### 8. Nginx als reverse proxy

Maak `/etc/nginx/sites-available/runai` aan:

```nginx
server {
    listen 80;
    server_name jouwdomein.nl www.jouwdomein.nl;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name jouwdomein.nl www.jouwdomein.nl;

    ssl_certificate     /etc/letsencrypt/live/jouwdomein.nl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jouwdomein.nl/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options    nosniff always;
    add_header X-Frame-Options           DENY always;
    add_header Referrer-Policy           strict-origin-when-cross-origin always;

    gzip on;
    gzip_types text/plain application/json application/javascript text/css;

    # Backend API
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        client_max_body_size 10M;
    }

    # API docs (verwijder in productie of beveilig met basic auth)
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }

    # Frontend
    location / {
        proxy_pass         http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection upgrade;
        proxy_set_header   Host       $host;
        proxy_set_header   X-Real-IP  $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/runai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 9. SSL met Certbot

```bash
sudo certbot --nginx -d jouwdomein.nl -d www.jouwdomein.nl

# Verifieer auto-renewal
sudo certbot renew --dry-run
sudo systemctl status certbot.timer
```

---

## Installatie op Alpine Linux

```bash
# Systeem pakketten
apk add --no-cache \
  python3 py3-pip py3-virtualenv \
  postgresql16 postgresql16-contrib \
  nginx certbot certbot-nginx \
  nodejs npm git curl gcc musl-dev \
  libpq-dev libffi-dev

# PostgreSQL starten
rc-update add postgresql default
rc-service postgresql start

# Daarna: zelfde stappen 3–7 als Debian
# Voor services: gebruik OpenRC i.p.v. systemd (zie hieronder)
```

### OpenRC services (Alpine)

**Backend** — `/etc/init.d/runai-backend`:

```bash
cat > /etc/init.d/runai-backend <<'EOF'
#!/sbin/openrc-run
description="RunAI Backend (FastAPI / Uvicorn)"

command="/home/runapp/app/backend/.venv/bin/uvicorn"
command_args="app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers"
directory="/home/runapp/app/backend"
command_user="runapp"
command_background=true
pidfile="/run/runai-backend.pid"
output_log="/var/log/runai-backend.log"
error_log="/var/log/runai-backend.log"

depend() {
    need net postgresql
}
EOF

chmod +x /etc/init.d/runai-backend
rc-update add runai-backend default
rc-service runai-backend start
```

**Frontend** — `/etc/init.d/runai-frontend`:

```bash
cat > /etc/init.d/runai-frontend <<'EOF'
#!/sbin/openrc-run
description="RunAI Frontend (Next.js)"

export NODE_ENV="production"
export PORT="3001"
export HOSTNAME="127.0.0.1"
export NEXT_PUBLIC_API_URL="https://jouwdomein.nl/api/v1"

command="/usr/bin/node"
command_args="/home/runapp/app/frontend/.next/standalone/server.js"
directory="/home/runapp/app/frontend"
command_user="runapp"
command_background=true
pidfile="/run/runai-frontend.pid"
output_log="/var/log/runai-frontend.log"
error_log="/var/log/runai-frontend.log"

depend() {
    need net runai-backend
}
EOF

chmod +x /etc/init.d/runai-frontend
rc-update add runai-frontend default
rc-service runai-frontend start
```

**Status controleren:**

```bash
rc-service runai-backend status
rc-service runai-frontend status

# Logs bekijken
tail -f /var/log/runai-backend.log
tail -f /var/log/runai-frontend.log
```

---

## Database back-ups

```bash
# /etc/cron.daily/runai-backup
#!/bin/bash
BACKUP_DIR="/var/backups/runai"
mkdir -p $BACKUP_DIR
sudo -u postgres pg_dump rundb | gzip > "$BACKUP_DIR/rundb_$(date +%Y%m%d_%H%M%S).sql.gz"
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

---

## Updates uitrollen

```bash
sudo su - runapp
cd ~/app
git pull

# Backend
cd backend
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Frontend
cd ../frontend
npm ci --frozen-lockfile
npm run build

# Herstarten
exit
sudo systemctl restart runai-backend runai-frontend
```

---

## Beveiligingschecklist

- [ ] `SECRET_KEY` is ≥ 32 willekeurige tekens
- [ ] `GARMIN_ENCRYPTION_KEY` is een geldige Fernet key
- [ ] `.env` is `chmod 600` (alleen eigenaar)
- [ ] PostgreSQL accepteert alleen lokale verbindingen (`pg_hba.conf`)
- [ ] Firewall: alleen poort 80/443 open naar buiten

```bash
# UFW (Debian)
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Alpine (iptables)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -j DROP
```

---

## Monitoring

```bash
# Logs
sudo journalctl -u runai-backend -f
sudo journalctl -u runai-frontend -f
sudo tail -f /var/log/nginx/access.log

# Services
sudo systemctl status runai-backend runai-frontend nginx postgresql

# Resources
htop
df -h && free -h
```
