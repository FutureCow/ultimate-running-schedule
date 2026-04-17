#!/usr/bin/env bash
# update.sh — pull latest code and rebuild only what changed
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
BACKEND_SERVICE="runai-backend"
FRONTEND_SERVICE="runai-frontend"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${BOLD}[update]${NC} $*"; }
success() { echo -e "${GREEN}[update]${NC} $*"; }
warn()    { echo -e "${YELLOW}[update]${NC} $*"; }
error()   { echo -e "${RED}[update]${NC} $*" >&2; exit 1; }

# ── Service manager detection ─────────────────────────────────────────────────
if command -v systemctl &>/dev/null && systemctl list-units --type=service &>/dev/null 2>&1; then
    restart_service() { sudo systemctl restart "$1" && success "Service $1 herstart (systemd)"; }
elif command -v rc-service &>/dev/null; then
    restart_service() { sudo rc-service "$1" restart && success "Service $1 herstart (OpenRC)"; }
else
    error "Geen ondersteunde service manager gevonden (systemd of OpenRC)."
fi

# ── Git pull ──────────────────────────────────────────────────────────────────
cd "$APP_DIR"
info "Git pull…"

BEFORE=$(git rev-parse HEAD)
git pull --ff-only || error "git pull mislukt. Los conflicten op en probeer opnieuw."
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
    success "Al up-to-date — niets te doen."
    exit 0
fi

# Bepaal welke bestanden zijn gewijzigd
CHANGED=$(git diff --name-only "$BEFORE" "$AFTER")
info "Gewijzigde bestanden:"
echo "$CHANGED" | sed 's/^/  /'

BACKEND_CHANGED=false
FRONTEND_CHANGED=false

echo "$CHANGED" | grep -q "^backend/" && BACKEND_CHANGED=true
echo "$CHANGED" | grep -q "^frontend/" && FRONTEND_CHANGED=true

# ── Backend update ────────────────────────────────────────────────────────────
if $BACKEND_CHANGED; then
    info "Backend bestanden gewijzigd — update starten…"
    cd "$BACKEND_DIR"

    source .venv/bin/activate

    # Alleen pip install als requirements.txt is veranderd
    if echo "$CHANGED" | grep -q "^backend/requirements"; then
        info "requirements.txt gewijzigd — dependencies installeren…"
        pip install -q -r requirements.txt
    fi

    # Alleen migraties als er nieuwe alembic versies zijn
    if echo "$CHANGED" | grep -q "^backend/alembic/versions/"; then
        info "Nieuwe migraties gevonden — alembic upgrade head…"
        alembic upgrade head
    fi

    deactivate
    restart_service "$BACKEND_SERVICE"
else
    warn "Backend ongewijzigd — overgeslagen."
fi

# ── Frontend update ───────────────────────────────────────────────────────────
if $FRONTEND_CHANGED; then
    info "Frontend bestanden gewijzigd — build starten…"
    cd "$FRONTEND_DIR"

    # Alleen npm ci als package-lock.json is veranderd
    if echo "$CHANGED" | grep -q "^frontend/package"; then
        info "package-lock.json gewijzigd — dependencies installeren…"
        npm ci --frozen-lockfile --silent
    fi

    info "Frontend bouwen…"
    npm run build

    info "Statische bestanden kopiëren…"
    cp -r .next/static .next/standalone/.next/static
    cp -r public .next/standalone/public

    restart_service "$FRONTEND_SERVICE"
else
    warn "Frontend ongewijzigd — overgeslagen."
fi

# ── Klaar ─────────────────────────────────────────────────────────────────────
echo ""
success "Update klaar! $(git log -1 --format='%h %s')"
