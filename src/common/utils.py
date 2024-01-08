
from src.common.logger import get_logger


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
        if isinstance(v, dict):
            sanitized_params[k] = sanitize_params_v2(
                v, hide_jwt=hide_jwt, hide_list=hide_list)

        elif isinstance(v, str) and len(v) > 64:
            sanitized_params[k] = f"{v[:64]}..truncated for print.."
            
        elif k in ['queue_consumer', 'basic_deliver']:
            continue

        elif hide_jwt is True and 'jwt' in k:
            continue
        
        elif hide_list is True and isinstance(v, list):
            sanitized_params[k] = f'List with {len(v)} items'
            
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
