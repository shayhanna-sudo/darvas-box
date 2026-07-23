"""Long-running scheduler service: fires the auto EOD run every weekday after US close."""
from apscheduler.schedulers.blocking import BlockingScheduler
import config
from src import auto
from src import telegram_bot as tg


def job():
    try:
        auto.main()
    except Exception as e:
        tg.send_message(f"Darvas service ERROR: {e}")
        print("[service] job error:", e)


def main():
    tg.send_message("Darvas service online - EOD scan scheduled 16:15 ET, Mon-Fri.")
    sched = BlockingScheduler(timezone="America/New_York")
    sched.add_job(job, "cron", day_of_week="mon-fri", hour=16, minute=15,
                  misfire_grace_time=3600)
    print("[service] scheduler started. Waiting for 16:15 ET...")
    sched.start()


if __name__ == "__main__":
    main()
