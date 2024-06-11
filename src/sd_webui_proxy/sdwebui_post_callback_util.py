from dataclasses import asdict
import json
from typing import List
from PIL import Image
from urllib.parse import urljoin

import src.config as config
from src.common.logger import get_logger
from src.sd_webui_proxy.type import SDWebUIPayload, SDInterrogatePayload, UpscaleBatchImagesListPayload, BatchImagesListType
from src.sd_webui_proxy.util import base64_to_image, image_to_base64, get_session, get_base64_data_from_redis

logger = get_logger()
session = get_session(config.SERVER_POST_RETRIES, config.SERVER_POST_BACKOFF)


def is_controlnet_args_present(payload: SDWebUIPayload):
    """
    Checks and returns whether there are controlnet arguments present in a config or not
    """
    return (
        payload.get('alwayson_scripts') is not None
        and payload.get('alwayson_scripts').get('controlnet') is not None
        and payload.get('alwayson_scripts').get('controlnet').get('args') is not None
        and len(payload.get('alwayson_scripts').get('controlnet').get('args', [])) > 0
    )


def replace_image_s3_url_to_base64(payload: SDWebUIPayload):
    """
    Replaces all s3 url redis keys with the corresponding base64 data so as to generate through SD WebUI
    """
    init_images = payload.get("init_images", [])
    if init_images:
        payload['init_images'] = [
            get_base64_data_from_redis(url) for url in init_images]

    for key in ["input_image", "mask"]:
        url = payload.get(key)
        if url:
            payload[key] = get_base64_data_from_redis(url)

    if is_controlnet_args_present(payload) is True:
        for cfg in payload['alwayson_scripts']['controlnet']['args']:
            cfg_input_image = cfg.get("input_image")
            if cfg_input_image:
                cfg["input_image"] = get_base64_data_from_redis(
                    cfg_input_image)


def post_request(url, payload, timeout=config.SERVER_POST_TIMEOUT):
    """
    Posts requests to SD WebUI server and returns the result
    """
    logger.info(f"Posting to {url}")
    response = session.post(url=url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response


def get_generated_images(requests):
    """
    For each config, image generation is triggered and returns generated_images base64 data
    """
    result_images = []
    seeds_list = []
    for request in requests:
        endpoint = request.get("endpoint", None)
        assert endpoint, "endpoint cannot be None"

        full_endpoint = urljoin(config.SD_WEBUI_API_ENDPOINT, endpoint)

        payload: SDWebUIPayload = request.get("payload", None)
        assert payload, "payload cannot be None"

        resize_payload = payload.get("resize_payload", None)
        no_of_samples = payload.get("batch_size", None)

        replace_image_s3_url_to_base64(payload)

        interrogate_model = request.get("interrogate_model", None)
        if interrogate_model:
            interrogate_endpoint = urljoin(
                config.SD_WEBUI_API_ENDPOINT, config.SD_WEBUI_INTERROGATE_ENDPOINT)

            interrogate_payload = asdict(SDInterrogatePayload(
                image=payload.get('init_images')[0],
                model=interrogate_model
            ))

            interrogate_response = post_request(
                url=interrogate_endpoint, payload=interrogate_payload)
            interrogate_prompt = interrogate_response.json()['caption']

            prompt = payload.get('prompt', "")
            payload['prompt'] = f"{interrogate_prompt} {prompt}"

        if len(result_images) > 0:
            result_image_selected = result_images[0]

            if "init_images" in payload:
                payload["init_images"] = [result_image_selected]

            if is_controlnet_args_present(payload) is True:
                for cfg in payload['alwayson_scripts']['controlnet']['args']:
                    cfg["input_image"] = result_image_selected

        response = post_request(url=full_endpoint, payload=payload)
        try:
            response_json = response.json()
            result_images = response_json.get("images", None) or [
                response_json.get("image", None)
            ]
            response_info = response_json.get("info")
            if response_info is not None:
                seeds_list = json.loads(response_info).get("all_seeds")

            if no_of_samples is not None:
                result_images = result_images[:no_of_samples]

            # If resize is required before inputing the output of one pipeline to the next pipeline
            if resize_payload is not None:
                resize_width, resize_height = resize_payload.get(
                    "resize_width"), resize_payload.get("resize_height")
                for ind, img in enumerate(result_images):
                    image = base64_to_image(img)
                    image = image.resize(
                        (resize_width, resize_height), Image.Resampling.LANCZOS)
                    b64_image = image_to_base64(image)
                    result_images[ind] = b64_image
        except Exception as e:
            logger.error("Error occurred: %s", str(e))
            result_images = []
            seeds_list = []
    return result_images, seeds_list


def get_resized_images(images: List, resize_width: int, resize_height: int) -> List:
    resized_images = []
    for img in images:
        decoded_image = base64_to_image(img)
        final_image = decoded_image.resize(
            (resize_width, resize_height), Image.LANCZOS)
        final_image_encoded = image_to_base64(final_image)
        resized_images.append(final_image_encoded)
    return resized_images


def get_upscaled_images(upscale_payload, result_images=None):
    """
    Returns upscaled images
    """
    upscale_full_endpoint = urljoin(
        config.SD_WEBUI_API_ENDPOINT, config.BATCH_UPSCALE_ENDPOINT)
    upscaled_images_list = upscale_payload.get("imageList", []) or []

    image_list = []
    if result_images and len(result_images) > 0:
        image_list = result_images
    else:
        for image in upscaled_images_list:
            image_list.append(get_base64_data_from_redis(image))

    assert image_list, "Upscale image list cannot be empty or None"
    upscaled_images_list = asdict(UpscaleBatchImagesListPayload(
        imageList=[
            asdict(BatchImagesListType(
                name=f"image_{index}", data=image))
            for index, image in enumerate(image_list)
        ]
    )
    )
    upscale_payload.update(upscaled_images_list)

    upscale_response = post_request(
        url=upscale_full_endpoint, payload=upscale_payload,)

    upscale_response_json = upscale_response.json()
    upscaled_images = upscale_response_json.get("images", [])

    return upscaled_images
