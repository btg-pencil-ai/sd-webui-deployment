import io
import base64
import logging
import requests
import time
import urllib3

import src.config as config

from PIL import Image
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin
from urllib3.util.retry import Retry

from src.common.logger import get_logger


urllib3.add_stderr_logger(level=logging.WARNING)


logger = get_logger(__name__)


def image_to_base64(image:Image):
    image_binary = io.BytesIO()
    image.save(image_binary, format='JPEG')
    binary_data = image_binary.getvalue()

    base64_data = base64.b64encode(binary_data).decode('utf-8')
    return base64_data


def base64_to_image(base64_image):
    binary_data = base64.b64decode(base64_image)

    # Convert binary data into a PIL Image object
    original_image = Image.open(io.BytesIO(binary_data))
    return original_image


def get_session(retries: int, backoff_factor: int):
    request_session = requests.Session()

    retries = Retry(total=retries, backoff_factor=backoff_factor)
    adapter = HTTPAdapter(max_retries=retries)
    
    request_session.mount('https://', adapter)
    request_session.mount('http://', adapter)

    return request_session


def check_server_readiness(init_sleep_seconds: int = 0):
    if init_sleep_seconds > 0:
        logger.info(f"check_server_readiness() - sleep for {init_sleep_seconds} s")
        time.sleep(init_sleep_seconds)

    session = get_session(config.SERVER_CHECK_RETRIES, config.SERVER_CHECK_BACKOFF)

    res = session.get(url=urljoin(config.SD_WEBUI_API_ENDPOINT, "/sdapi/v1/progress"),
                      timeout=config.SERVER_CHECK_TIMEOUT)
    res.raise_for_status()

    logger.info(f"check_server_readiness() - response: {res.json()}")

    # Ready means job count is 0 in this dict structure
    ready = res.json().get('state', {}).get('job_count', None) == 0

    return ready

def url_to_base64_image(url):
    try:
        response = requests.get(url)

        if response.status_code == 200:
            # Encode the image data as a Base64 string
            base64_image = base64.b64encode(response.content).decode("utf-8")
            return base64_image
        else:
            print(f"Failed to fetch the image. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
