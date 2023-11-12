
from src.common.logger import get_logger


logger = get_logger(__name__)


def sanitize_params_for_print(params, hide_jwt=True, hide_list=False):
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
