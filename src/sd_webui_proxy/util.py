import io
import json
import os
import base64
import logging
import requests
import time
import urllib3
import uuid
import tempfile
from src.sd_webui_proxy.constant import AI_MAGIC_TOOLS_REDIS_KEY_PREFIX
from src.aws.aws import s3_public_url, upload_to_s3
from src.common.redis import redis_connection

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

def image_to_base64(image:Image, format="JPEG"):
    image_binary = io.BytesIO()
    image.save(image_binary, format=format)
    binary_data = image_binary.getvalue()

    base64_data = base64.b64encode(binary_data).decode('utf-8')
    return base64_data

def base64_to_image(base64_image):
    binary_data = base64.b64decode(base64_image)

    # Convert binary data into a PIL Image object
    original_image = Image.open(io.BytesIO(binary_data))
    return original_image

def set_redis_key(redis_key: str, base64_str: str):
    redis_connection.set(redis_key, base64_str)
    redis_connection.expire(redis_key, config.IMAGE_GENERATION_REDIS_EXPIRE)

def get_by_redis_key(redis_key: str) -> str:
    value = redis_connection.get(redis_key)  
    return value

def set_base64_data_to_redis(base64_image:str)->str:
    s3_key = f"{str(uuid.uuid4())}.jpg"
    s3_url = s3_public_url(bucket=config.S3_BUCKET,key=s3_key)

    logger.info(f"Setting image base64 data to redis key:{s3_url}")
    set_redis_key(s3_url, base64_image)
    return s3_url

def get_base64_data_from_redis(s3_url):
    logger.info("Re-using image base64 from redis")
    base64_image = get_by_redis_key(redis_key=s3_url)
    base64_image = base64_image.decode('utf-8')
    return base64_image

def get_generated_image_s3_key(
    base_filename: str, client_id: int, batch_uuid: str, image_ext: str
) -> str:
    return f"{os.path.join(base_filename,str(client_id),batch_uuid, str(uuid.uuid4()))}.{image_ext}"

def upload_base64_to_s3(base64_data, s3_key):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_image_data = base64.b64decode(base64_data)
        file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
        with open(file_path, "wb") as file:
            file.write(input_image_data)
        upload_to_s3(
            filename=file_path,
            bucket=config.AWS_S3_BUCKET,
            key=s3_key,
            public=True,
        )

def set_redis_keys_tracking_key(job_id, redis_keys_list):
    redis_key = f"{AI_MAGIC_TOOLS_REDIS_KEY_PREFIX}_{job_id}"
    redis_keys_list_bytes = json.dumps(redis_keys_list)
    logger.info("Setting all keys to redis")
    set_redis_key(redis_key=redis_key,value=redis_keys_list_bytes,expiry=7200)