#!/bin/sh
# update.sh — pull latest code and rebuild only what changed
#
# Usage:
#   ./update.sh              — normaal: git pull, update alleen wat gewijzigd is
#   ./update.sh --backend    — forceer backend update (ook zonder git-wijzigingen)
#   ./update.sh --frontend   — forceer frontend update (ook zonder git-wijzigingen)
#   ./update.sh --both       — forceer beide
#
# Compatible with bash, sh, and busybox ash (Alpine Linux)
set -eu

# ── Config ────────────────────────────────────────────────────────────────────
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
BACKEND_SERVICE="runai-backend"
FRONTEND_SERVICE="runai-frontend"

# ── Argument parsing ──────────────────────────────────────────────────────────
FORCE_BACKEND=false
FORCE_FRONTEND=false

for arg in "$@"; do
    case "$arg" in
        --backend)  FORCE_BACKEND=true ;;
        --frontend) FORCE_FRONTEND=true ;;
        --both)     FORCE_BACKEND=true; FORCE_FRONTEND=true ;;
        *) printf 'Onbekend argument: %s\nGebruik: ./update.sh [--backend|--frontend|--both]\n' "$arg" >&2; exit 1 ;;
    esac
done

# ── Colour helpers ────────────────────────────────────────────────────────────
info()    { printf '\033[1m[update]\033[0m %s\n' "$*"; }
success() { printf '\033[0;32m[update]\033[0m %s\n' "$*"; }
warn()    { printf '\033[1;33m[update]\033[0m %s\n' "$*"; }
error()   { printf '\033[0;31m[update]\033[0m %s\n' "$*" >&2; exit 1; }

# ── Service manager detection ─────────────────────────────────────────────────
if command -v systemctl >/dev/null 2>&1 && systemctl list-units --type=service >/dev/null 2>&1; then
    restart_service() { sudo systemctl restart "$1" && success "Service $1 herstart (systemd)"; }
elif command -v rc-service >/dev/null 2>&1; then
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

# Bepaal gewijzigde bestanden (leeg als er niets veranderd is)
if [ "$BEFORE" != "$AFTER" ]; then
    CHANGED=$(git diff --name-only "$BEFORE" "$AFTER")
    info "Gewijzigde bestanden:"
    echo "$CHANGED" | sed 's/^/  /'
else
    CHANGED=""
fi

BACKEND_CHANGED=false
FRONTEND_CHANGED=false

echo "$CHANGED" | grep -q "^backend/"  && BACKEND_CHANGED=true || true
echo "$CHANGED" | grep -q "^frontend/" && FRONTEND_CHANGED=true || true

# Forceer-vlaggen overschrijven git-detectie
$FORCE_BACKEND  && BACKEND_CHANGED=true
$FORCE_FRONTEND && FRONTEND_CHANGED=true

if ! $BACKEND_CHANGED && ! $FRONTEND_CHANGED; then
    success "Al up-to-date — niets te doen. Gebruik --backend, --frontend of --both om geforceerd te updaten."
    exit 0
fi

# ── Backend update ────────────────────────────────────────────────────────────
if $BACKEND_CHANGED; then
    if $FORCE_BACKEND && [ -z "$CHANGED" ]; then
        info "Backend geforceerd updaten (geen git-wijzigingen)…"
    else
        info "Backend bestanden gewijzigd — update starten…"
    fi
    cd "$BACKEND_DIR"

    . .venv/bin/activate

    # pip install: altijd bij --backend force, anders alleen als requirements veranderd is
    if $FORCE_BACKEND || echo "$CHANGED" | grep -q "^backend/requirements"; then
        info "Dependencies installeren…"
        pip install -q -r requirements.txt
    fi

    # Migraties: altijd bij --backend force, anders alleen als er nieuwe versies zijn
    if $FORCE_BACKEND || echo "$CHANGED" | grep -q "^backend/alembic/versions/"; then
        info "Alembic upgrade head…"
        alembic upgrade head
    fi

    deactivate
    restart_service "$BACKEND_SERVICE"
else
    warn "Backend ongewijzigd — overgeslagen."
fi

# ── Frontend update ───────────────────────────────────────────────────────────
if $FRONTEND_CHANGED; then
    if $FORCE_FRONTEND && [ -z "$CHANGED" ]; then
        info "Frontend geforceerd updaten (geen git-wijzigingen)…"
    else
        info "Frontend bestanden gewijzigd — build starten…"
    fi
    cd "$FRONTEND_DIR"

    # npm ci: altijd bij --frontend force, anders alleen als package-lock veranderd is
    if $FORCE_FRONTEND || echo "$CHANGED" | grep -q "^frontend/package"; then
        info "Dependencies installeren…"
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
printf '\n'
success "Update klaar! $(git log -1 --format='%h %s')"
