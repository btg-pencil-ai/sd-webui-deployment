import os
import requests

import src.config as config

from urllib.parse import urljoin

from src.common import amqp
from src.common.logger import get_logger


logger = get_logger()


def sd_webui_post_callback_processor(params):
    callback_routing_key = os.environ.get('SD_WEBUI_CALLBACK_ROUTING_KEY', '*.sdwebui.callback.processor')

    try:
        endpoint = params.get('endpoint', None)
        assert endpoint is not None, "endpoint is None"

        payload = params.get('payload', None)
        assert payload is not None, "payload is None"

        full_endpoint = urljoin(config.SD_WEBUI_API_ENDPOINT, endpoint)
        logger.info(f"Posting to {full_endpoint}")

        response = requests.post(full_endpoint, json=payload, timeout=300)
        response.raise_for_status()
        
        amqp.publish(config.EXCHANGE_NAME, callback_routing_key, response.json(), None, 255)
        logger.info(f'Published to callback queue {callback_routing_key}')
    
    except Exception as e:
        logger.error(e, exc_info=True)
