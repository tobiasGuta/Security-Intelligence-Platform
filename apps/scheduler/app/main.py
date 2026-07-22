import time
import signal
import sys
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog
from app.schedules import register_schedules

class Settings(BaseSettings):
    REDIS_URL: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
logger = structlog.get_logger()

# Configure Dramatiq Broker
redis_broker = RedisBroker(url=settings.REDIS_URL)
dramatiq.set_broker(redis_broker)

def main():
    from urllib.parse import urlparse
    parsed = urlparse(settings.REDIS_URL)
    jobstores = {
        'default': RedisJobStore(
            jobs_key='apscheduler.jobs',
            run_times_key='apscheduler.run_times',
            host=parsed.hostname,
            port=parsed.port,
            password=parsed.password,
            db=0
        )
    }

    scheduler = BackgroundScheduler(jobstores=jobstores)
    register_schedules(scheduler)

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
