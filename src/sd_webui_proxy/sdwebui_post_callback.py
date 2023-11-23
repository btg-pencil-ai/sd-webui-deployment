from dataclasses import asdict
from PIL import Image
import os
import requests

import src.config as config

from requests.adapters import HTTPAdapter
from urllib.parse import urljoin
from urllib3.util.retry import Retry

from src.common import amqp
from src.common.logger import get_logger
from src.sd_webui_proxy.type import UpscaleBatchImagesListPayload, BatchImagesListType
from src.sd_webui_proxy.util import base64_to_image, image_to_base64, get_session


logger = get_logger()


def sd_webui_post_callback_processor(params):
    session = get_session(config.SERVER_POST_RETRIES, config.SERVER_POST_BACKOFF)

    try:
        callback_message = params.get('callback_message', {})

        callback_routing_key = callback_message.get('routing_key', None)
        assert callback_routing_key is not None, "callback_routing_key not provided"

        callback_payload = callback_message.get('payload', None)
        assert callback_payload is not None, "callback payload not provided"

        callback_priority = callback_message.get('callback_priority', 255)

        endpoint = params.get('endpoint', None)
        assert endpoint is not None, "endpoint is None"

        full_endpoint = urljoin(config.SD_WEBUI_API_ENDPOINT, endpoint)

        payload = params.get('payload', None)
        assert payload is not None , "payload is None"#check

        sd_webui_options_payload = params.get('sd_webui_options_payload', None)
        upscale_payload = params.get('upscale_payload', None)

        no_of_samples = payload.get("batch_size", None)

        width = callback_payload.get("gen_image_width")
        height = callback_payload.get("gen_image_height")

        if sd_webui_options_payload is not None:
            set_sd_webui_options_full_endpoint = urljoin(config.SD_WEBUI_API_ENDPOINT, 
                                                         config.SET_SD_WEBUI_OPTIONS_ENDPOINT)

            #response = requests.post(set_sd_webui_options_full_endpoint, json=sd_webui_options_payload, timeout=300)
            response = session.post(url=set_sd_webui_options_full_endpoint, 
                                    json=sd_webui_options_payload,
                                    timeout=config.SERVER_POST_TIMEOUT)
            response.raise_for_status()

            logger.info(f'Completed switching models')

        logger.info(f"Posting to {full_endpoint}")
        #response = requests.post(full_endpoint, json=payload, timeout=300)
        response = session.post(url=full_endpoint, json=payload, timeout=config.SERVER_POST_TIMEOUT)
        response.raise_for_status()

        response_json = response.json()
        result_images = response_json.get("images",None)

        if no_of_samples is not None:
            result_images = result_images[:no_of_samples]

        if(upscale_payload is not None):
            upscale_full_endpoint = urljoin(config.SD_WEBUI_API_ENDPOINT, config.BATCH_UPSCALE_ENDPOINT)
            
            upscaled_images_list = asdict(UpscaleBatchImagesListPayload(
                imageList=[asdict((BatchImagesListType(name=f"image_{index}",data=image))) 
                           for index,image in enumerate(result_images)]))
            upscale_payload.update(upscaled_images_list)
            
            #upscale_response = requests.post(upscale_full_endpoint, json=upscale_payload, timeout=300)
            upscale_response = session.post(url=upscale_full_endpoint, 
                                            json=upscale_payload, 
                                            timeout=config.SERVER_POST_TIMEOUT)
            upscale_response.raise_for_status()

            upscale_response_json = upscale_response.json()
            upscaled_images = upscale_response_json.get("images",[]) 

            resized_images = []
            for img in upscaled_images:
                decoded_image = base64_to_image(img)
                final_image = decoded_image.resize((width, height), Image.LANCZOS)
                final_image_encoded = image_to_base64(final_image)
                resized_images.append(final_image_encoded)
            result_images = list(filter(None, resized_images))

        callback_payload["base64_images"] = result_images
    
    except Exception as e:
        callback_payload["base64_images"] = None
        logger.error(e, exc_info=True)

    finally:
        amqp.publish(config.EXCHANGE_NAME, 
                     callback_routing_key, 
                     callback_payload, 
                     None, 
                     callback_priority)
        logger.info(f'Published to callback queue {callback_routing_key}')