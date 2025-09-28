# APScheduler Orchestrator (skeleton)
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

