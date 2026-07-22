import dramatiq
from dramatiq.brokers.redis import RedisBroker
from app.core.config import get_settings
import structlog

settings = get_settings()
redis_broker = RedisBroker(url=settings.REDIS_URL)
dramatiq.set_broker(redis_broker)

logger = structlog.get_logger()
logger.info("Worker starting up with Redis broker")

# Actors will be imported here in later milestones
