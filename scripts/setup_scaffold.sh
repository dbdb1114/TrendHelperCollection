#!/usr/bin/env bash
set -euo pipefail

### === Helpers ===
log()  { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[DONE]\033[0m %s\n" "$*"; }

ROOT_DIR="$(pwd)"

ensure_dir() {
  [[ -d "$1" ]] || { mkdir -p "$1"; log "mkdir -p $1"; }
}

ensure_file() {
  local path="$1"; shift
  if [[ -f "$path" ]]; then
    log "exists: $path"
  else
    mkdir -p "$(dirname "$path")"
    cat > "$path" <<'EOF'
'"$@"'
EOF
    # 위 trick은 빈 here-doc 방지를 위해 남겨둠 (내용은 아래 개별 작성 함수들이 넣습니다)
  fi
}

write_if_missing() {
  local path="$1"; shift
  if [[ -f "$path" ]]; then
    log "exists: $path"
  else
    mkdir -p "$(dirname "$path")"
    cat > "$path" <<EOF
$*
EOF
    log "created: $path"
  fi
}

append_unique_lines() {
  local path="$1"; shift
  mkdir -p "$(dirname "$path")"
  [[ -f "$path" ]] || touch "$path"
  while IFS= read -r line; do
    grep -qxF "$line" "$path" || echo "$line" >> "$path"
  done <<< "$*"
  log "updated: $path"
}

have() { command -v "$1" >/dev/null 2>&1; }


### === 0) Basic files ===
log "Setting up baseline files..."

append_unique_lines ".gitignore" '
.env
__pycache__/
*.pyc
*.pyo
.mypy_cache/
.pytest_cache/
.coverage
dist/
build/
.eggs/
.cache/
.DS_Store
.ipynb_checkpoints/
'

write_if_missing ".dockerignore" '
.git
.mypy_cache
.pytest_cache
__pycache__
*.pyc
.env
*.log
dist
build
'

write_if_missing ".env.sample" 'DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/trendhelper
YOUTUBE_API_KEY=
ANTHROPIC_API_KEY=
REDIS_URL=redis://localhost:6379/0
APP_ENV=dev
TZ=UTC
'

# minimal README if missing
write_if_missing "README.md" '# Trend Helper (skeleton)
See CLAUDE.md at root and module-specific CLAUDE.md files for instructions.
'

### === 1) Alembic bootstrap (env.py & versions dir) ===
log "Configuring Alembic..."

# Ensure migrations structure
ensure_dir "migrations/versions"

# Create alembic.ini if missing (placeholder)
if [[ ! -f "alembic.ini" ]]; then
  write_if_missing "alembic.ini" '# placeholder; run `alembic init migrations` later to generate proper config'
  warn "alembic.ini not found; created placeholder."
fi

if [[ ! -f "migrations/env.py" ]]; then
  if have alembic; then
    warn "migrations/env.py missing — attempting \`alembic init migrations\` ..."
    # Only init if migrations dir is empty (except versions/)
    if [[ -z "$(ls -A migrations | grep -v versions || true)" ]]; then
      alembic init migrations || warn "alembic init failed; will create minimal env.py manually."
    fi
  fi
fi

# If still missing, create a minimal env.py that reads DATABASE_URL.
if [[ ! -f "migrations/env.py" ]]; then
  write_if_missing "migrations/env.py" '# Minimal Alembic env.py (manual template)
import os
from alembic import context
from sqlalchemy import create_engine
from logging.config import fileConfig

# If you later generate a proper alembic.ini, fileConfig can read it
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your Base metadata here when ready:
# from core.models import Base
target_metadata = None  # replace with Base.metadata when models are ready

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/trendhelper")

def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(DATABASE_URL, pool_pre_ping=True)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'
  ok "created minimal migrations/env.py"
else
  log "exists: migrations/env.py"
fi

### === 2) Scheduler runner stub ===
log "Creating APScheduler runner stub..."

write_if_missing "jobs/runner.py" '# APScheduler Orchestrator (skeleton)
from __future__ import annotations
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("runner")

def safe(fn):
    def _wrap():
        try:
            fn()
        except Exception:
            log.exception("Job failed: %%s", getattr(fn, "__name__", "unknown"))
    return _wrap

# Optional imports; keep tolerant if files are not ready
def _nop():
    log.info("NOP job — replace with real job when ready.")

try:
    from collection.jobs.collector_trending import main as collect_trending
except Exception:
    collect_trending = _nop

try:
    from collection.jobs.collector_incremental import main as collect_incremental
except Exception:
    collect_incremental = _nop

try:
    from analysis.jobs.analyzer_velocity import main as analyze_velocity
except Exception:
    analyze_velocity = _nop

if __name__ == "__main__":
    sched = BlockingScheduler(timezone="UTC")
    # every 60 minutes at minute 0
    sched.add_job(safe(collect_trending), CronTrigger(minute="0"))
    # at minute 30
    sched.add_job(safe(collect_incremental), CronTrigger(minute="30"))
    # at minute 45
    sched.add_job(safe(analyze_velocity), CronTrigger(minute="45"))
    log.info("Scheduler starting (UTC)...")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
'

### === 3) Config template ===
log "Adding config template..."

ensure_dir "configs"
write_if_missing "configs/settings.example.yaml" 'env: ${APP_ENV}
timezone: UTC

database:
  url: ${DATABASE_URL}

redis:
  url: ${REDIS_URL}

apis:
  youtube: ${YOUTUBE_API_KEY}
  anthropic: ${ANTHROPIC_API_KEY}

scheduler:
  interval_minutes: 60
'

### === 4) Minimal FastAPI app (if not present) ===
log "Ensuring minimal FastAPI app..."

write_if_missing "app/main.py" 'from fastapi import FastAPI

app = FastAPI(title="Trend Helper API", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True}
'

### === 5) Core DB stub (if not present) ===
write_if_missing "core/db.py" '# placeholder for SQLAlchemy engine/session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/trendhelper")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
'

### === 6) Gentle reminders ===
warn "Choose ONE dependency file as your source of truth (pyproject.toml OR requirements.txt). Script did not delete anything."
warn "Run \`python -m venv .venv && source .venv/bin/activate\` and install deps when ready."
warn "If you later install Alembic, regenerate official env with \`alembic init migrations\` and keep your versions dir."

ok "Scaffold/checklist complete. ✅"
echo "Next steps:"
echo "  1) cp .env.sample .env  # and fill keys"
echo "  2) (venv) pip install fastapi uvicorn[standard] sqlalchemy psycopg[binary] alembic apscheduler pandas scikit-learn konlpy httpx pydantic-settings redis"
echo "  3) python -m uvicorn app.main:app --reload"
echo "  4) python jobs/runner.py"
