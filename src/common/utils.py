
from typing import Optional
from src.common.logger import get_logger
from pottery import Redlock
from redis import Redis

logger = get_logger(__name__)


def sanitize_params_v1(params, hide_jwt=True, hide_list=False):
    sanitized_params = {}

    for k, v in params.items():
        if k in ['queue_consumer', 'basic_deliver']:
            continue

        if hide_jwt is True and 'jwt' in k:
            continue

        if hide_list is True and isinstance(v, list):
            sanitized_params[k] = f'List with {len(v)} items'
            continue

        if isinstance(v, str) and len(v) > 64:
            v = f"{v[:64]}..truncated for print.."

        sanitized_params[k] = v

    return sanitized_params


def sanitize_params_v2(params, hide_jwt=True, hide_list=False):
    # Recursively clean up dict (e.g. callback params etc.)
    sanitized_params = {}
    for k, v in params.items():
        if k in ['queue_consumer', 'basic_deliver']:
            continue

        elif hide_jwt is True and 'jwt' in k:
            continue

        elif hide_list is True and isinstance(v, list):
            sanitized_params[k] = f'List with {len(v)} items'

        elif isinstance(v, str) and len(v) > 64:
            sanitized_params[k] = f"{v[:64]}..truncated for print.."

        elif isinstance(v, dict):
            sanitized_params[k] = sanitize_params_v2(
                v, hide_jwt=hide_jwt, hide_list=hide_list)

        else:
            sanitized_params[k] = v

    return sanitized_params


def sanitize_params_for_print(params, hide_jwt=True, hide_list=False):
    try:
        sanitized_params = sanitize_params_v2(
            params, hide_jwt=hide_jwt, hide_list=hide_list)
        
    except Exception as e:
        logger.error(e, exc_info=True)
        sanitized_params = sanitize_params_v1(
            params, hide_jwt=hide_jwt, hide_list=hide_list)

    return sanitized_params


def print_sanitized_params(params, hide_jwt=True, hide_list=False):
    sanitized_params = sanitize_params_for_print(
        params, hide_jwt=hide_jwt, hide_list=hide_list)

    logger.info('-' * 30)
    logger.info('Params:')

    for k, v in sanitized_params.items():
        try:
            logger.info(f'{k}: {v}')

        except Exception as e:
            logger.info(f'{k}: Unable to serialize. E:{e}')

    logger.info('-' * 30)

def acquire_redis_lock(redis_connection: Redis, redis_lock_key: str,
                       expire: Optional[float] = 30,
                       auto_renewal: Optional[bool] = False,
                       blocking: Optional[bool] = True):
    if auto_renewal is True:
        logger.warning("Moved to safer pottery.Redlock implementation - auto_renewal not supported!")

    if redis_lock_key is not None:
        redis_lock_object = Redlock(key=redis_lock_key,
                                    masters={redis_connection},
                                    auto_release_time=int(expire * 1000))

        # Block code here until we can get the lock
        logger.info("Waiting to acquire redis lock %s" % redis_lock_key)
        if redis_lock_object.acquire(blocking=blocking, timeout=expire):
            pass

        else:
            logger.warning(f"Failed to get lock {redis_lock_key} after {expire} seconds - going ahead anyway!")

    else:
        logger.warning("No lock to acquire (key is None)")
        redis_lock_object = None

    return redis_lock_object


def release_redis_lock(redis_lock_object):
    if redis_lock_object is not None:
        try:
            logger.info("Release redis lock")
            redis_lock_object.release()

        except Exception as e:
            logger.warning(e, exc_info=True)
