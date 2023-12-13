from dataclasses import asdict
from PIL import Image
from urllib.parse import urljoin

import src.config as config
from src.common.logger import get_logger
from src.sd_webui_proxy.type import UpscaleBatchImagesListPayload, BatchImagesListType
from src.sd_webui_proxy.util import base64_to_image, image_to_base64, get_session

logger = get_logger()
session = get_session(config.SERVER_POST_RETRIES, config.SERVER_POST_BACKOFF)


def post_request(url, payload, timeout=config.SERVER_POST_TIMEOUT):
    logger.info(f"Posting to {url}")
    response = session.post(url=url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response

def get_generated_images(requests):

    result_images = []
    for request in requests:
        endpoint = request.get("endpoint", None)
        full_endpoint = urljoin(config.SD_WEBUI_API_ENDPOINT, endpoint)
        payload = request.get("payload", None)
        resize_payload = payload.get("resize_payload",None)
        no_of_samples = payload.get("batch_size", None)

        if len(result_images) > 0:
            result_image_selected = result_images[0]
            payload["init_images"] = [result_image_selected]
            
            if payload.get("alwayson_scripts",{}) and payload["alwayson_scripts"].get("controlnet",{}) and payload["alwayson_scripts"]["controlnet"].get("args",None):
                controlnet_configs = payload["alwayson_scripts"]["controlnet"]["args"]
                for cfg in controlnet_configs:
                    cfg["input_image"] = result_image_selected
                payload["alwayson_scripts"]["controlnet"]["args"] = controlnet_configs
                
        response = post_request(url=full_endpoint, payload=payload)
        try:
            response_json = response.json()
            result_images = response_json.get("images", None) or [
                response_json.get("image", None)
            ]
            if no_of_samples is not None:
                result_images = result_images[:no_of_samples]

            if resize_payload is not None:
                resize_width, resize_height = resize_payload.get("resize_width"), resize_payload.get("resize_height")
                for ind,img in enumerate(result_images):
                    image = base64_to_image(img)
                    image = image.resize((resize_width,resize_height),Image.Resampling.LANCZOS)
                    b64_image = image_to_base64(image)
                    result_images[ind] = b64_image
        except:
            result_images = []
    return result_images

def get_upscaled_images(upscale_payload, resize_width, resize_height, result_images=None):
    upscale_full_endpoint = urljoin(config.SD_WEBUI_API_ENDPOINT, config.BATCH_UPSCALE_ENDPOINT)
    upscaled_images_list = upscale_payload.get("imageList",None)

    if upscaled_images_list is None:
        upscaled_images_list = asdict(
            UpscaleBatchImagesListPayload(
                imageList=[
                    asdict((BatchImagesListType(name=f"image_{index}", data=image)))
                    for index, image in enumerate(result_images)
                ]
            )
        )
        upscale_payload.update(upscaled_images_list)

    upscale_response = post_request(url=upscale_full_endpoint,payload=upscale_payload,)

    upscale_response_json = upscale_response.json()
    upscaled_images = upscale_response_json.get("images", [])

    resized_images = []
    for img in upscaled_images:
        decoded_image = base64_to_image(img)
        final_image = decoded_image.resize((resize_width, resize_height), Image.LANCZOS)
        final_image_encoded = image_to_base64(final_image)
        resized_images.append(final_image_encoded)
    
    return resized_images