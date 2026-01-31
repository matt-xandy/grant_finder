from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import get_settings
from .pipeline.run import run_pipeline


def start_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.run_timezone)
    trigger = CronTrigger(hour=settings.run_hour, minute=settings.run_minute)
    scheduler.add_job(run_pipeline, trigger=trigger, id="daily-run", replace_existing=True)
    scheduler.start()
    return scheduler
