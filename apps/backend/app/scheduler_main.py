import time
import signal
import sys
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from apscheduler.jobstores.redis import RedisJobStore  # type: ignore
from app.core.config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()

redis_broker = RedisBroker(url=settings.REDIS_URL)
dramatiq.set_broker(redis_broker)


def main():
    from urllib.parse import urlparse

    parsed = urlparse(settings.REDIS_URL)
    jobstores = {
        "default": RedisJobStore(
            jobs_key="apscheduler.jobs",
            run_times_key="apscheduler.run_times",
            host=parsed.hostname,
            port=parsed.port,
            password=parsed.password,
            db=0,
        )
    }

    scheduler = BackgroundScheduler(jobstores=jobstores)

    def shutdown_handler(signum, frame):
        logger.info("Received termination signal, shutting down scheduler...")
        scheduler.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    logger.info("Starting scheduler...")
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
