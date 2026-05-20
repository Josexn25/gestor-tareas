import os
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services.reminders import run_reminder_check


scheduler = BackgroundScheduler()


def start_reminder_scheduler(app):
    """Inicia el scheduler automatico de recordatorios."""
    if os.environ.get("ENABLE_REMINDER_SCHEDULER", "true").lower() != "true":
        app.logger.info("Scheduler de recordatorios desactivado por ENABLE_REMINDER_SCHEDULER.")
        return

    if scheduler.running:
        return

    timezone_name = app.config.get("APP_TIMEZONE", "America/Bogota")
    check_hour = int(os.environ.get("REMINDER_CHECK_HOUR", "8"))

    def job():
        with app.app_context():
            run_reminder_check()

    scheduler.add_job(
        job,
        CronTrigger(hour=check_hour, minute=0, timezone=ZoneInfo(timezone_name)),
        id="task_email_reminders",
        replace_existing=True,
    )
    scheduler.start()
    app.logger.info("Scheduler de recordatorios activo en %s a las %s:00.", timezone_name, check_hour)
