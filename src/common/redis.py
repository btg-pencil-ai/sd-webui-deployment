import os
import redis

from src.common.logger import get_logger
from src.config import TEST_MODE

logger = get_logger(__name__)

if TEST_MODE:
    from unittest import mock

    redis_connection = mock.Mock()

else:
    try:
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_db = int(os.environ.get('REDIS_DB', 0))

        logger.info(f'Connecting to Redis at {redis_host}:{redis_port}')
        pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=redis_db)
        redis_connection = redis.Redis(connection_pool=pool)
        logger.info(f'Connected to Redis')
        redis_connection.ping()

        logger.info(f'Redis connection test successful!!!')

    except Exception as ee:
        logger.debug(ee, exc_info=True)