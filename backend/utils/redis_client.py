"""
Redis Client Utility
Provides a global Redis connection instance and checking functions.
"""

import logging
import redis
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Initialize the raw Redis client
# decode_responses=True ensures we get Python strings instead of bytes
try:
    redis_client = redis.Redis.from_url(
        config.REDIS_URL,
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
    )
    logger.info(f"Initialized Redis client connecting to {config.REDIS_URL}")
except Exception as e:
    logger.error(f"Failed to initialize Redis client: {str(e)}")
    redis_client = None


def is_redis_available() -> bool:
    """Check if the Redis server is currently reachable."""
    # Disable Redis during testing to avoid database/cache state pollution
    if get_config().TESTING:
        return False
    if redis_client is None:
        return False
    try:
        return bool(redis_client.ping())
    except Exception as e:
        logger.warning(f"Redis is not available: {str(e)}")
        return False
