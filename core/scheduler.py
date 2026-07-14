import schedule
import time
import threading
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_scheduler_thread = None

def _run_scheduler():
    logger.info("Background scheduler thread started.")
    while not _stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)
    logger.info("Background scheduler thread stopped.")

def start_scheduler():
    global _scheduler_thread
    if _scheduler_thread is None or not _scheduler_thread.is_alive():
        _stop_event.clear()
        _scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True, name="JarvisSchedulerThread")
        _scheduler_thread.start()

def stop_scheduler():
    _stop_event.set()
    if _scheduler_thread:
        _scheduler_thread.join(timeout=2)

def schedule_task(job_func: Callable, interval: int, unit: str, run_once: bool = False):
    """
    Schedules a job.
    interval: The number of units.
    unit: 'seconds', 'minutes', 'hours', 'days'.
    run_once: If True, the job cancels itself after running.
    """
    if unit == "seconds":
        job = schedule.every(interval).seconds
    elif unit == "minutes":
        job = schedule.every(interval).minutes
    elif unit == "hours":
        job = schedule.every(interval).hours
    elif unit == "days":
        job = schedule.every(interval).days
    else:
        logger.error(f"Unknown scheduling unit: {unit}")
        return False

    def wrapped_job():
        logger.info(f"Executing scheduled task.")
        try:
            job_func()
        except Exception as e:
            logger.error(f"Error executing scheduled task: {e}")
        if run_once:
            return schedule.CancelJob

    job.do(wrapped_job)
    logger.info(f"Scheduled task every {interval} {unit} (run_once={run_once}).")
    return True
