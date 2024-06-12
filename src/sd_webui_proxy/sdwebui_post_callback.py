from urllib.parse import urljoin

import src.config as config
from src.common import amqp
from src.common.logger import get_logger
from src.sd_webui_proxy.util import get_redis_keys_tracking_key, set_base64_data_to_redis, set_redis_keys_tracking_key
from src.sd_webui_proxy.sdwebui_post_callback_util import get_resized_images, post_request, get_generated_images, get_upscaled_images

logger = get_logger()


def sd_webui_post_callback_processor(params):
    """
    Accepts config from genai-server and preprocess the config to send to SD WebUI worker.
    Post generation the images will be sent to callback queue with the callback_payload + generated_images
    """
    try:
        callback_message = params.get("callback_message", {})

        callback_routing_key = callback_message.get("routing_key", None)
        assert callback_routing_key is not None, "callback_routing_key not provided"

        callback_payload = callback_message.get("payload", None)
        assert callback_payload is not None, "callback payload not provided"

        callback_priority = callback_message.get("callback_priority", 255)

        requests = params.get("requests", []) or []

        sd_webui_options_payload = params.get("sd_webui_options_payload", None)
        upscale_payload = params.get("upscale_payload", None)

        width = callback_payload.get("gen_image_width")
        height = callback_payload.get("gen_image_height")

        job_id = callback_payload.get("job_id")

        redis_keys_list = get_redis_keys_tracking_key(job_id=job_id)

        if sd_webui_options_payload is not None:
            set_sd_webui_options_full_endpoint = urljoin(
                config.SD_WEBUI_API_ENDPOINT, config.SET_SD_WEBUI_OPTIONS_ENDPOINT
            )
            post_request(url=set_sd_webui_options_full_endpoint,payload=sd_webui_options_payload,)
            logger.info("Completed switching models")

        # Generate images using SD WebUI
        result_images = []
        all_seeds_list = []
        for request in requests:
            images_list, seeds_list = get_generated_images(request)
            result_images.extend(images_list)
            all_seeds_list.extend(seeds_list)

        # Upscale the generated images
        if upscale_payload is not None:
            upscaled_images = get_upscaled_images(upscale_payload=upscale_payload, result_images=result_images)
            result_images = list(filter(None, upscaled_images))

        # Resize if required
        if width is not None and height is not None:
            result_images = get_resized_images(images=result_images, resize_width=width, resize_height=height)

        # To pass it on save the base64 data to redis keys and update the tracking keys list
        result_images_s3_urls = []
        for result_image in result_images:
            s3_url = set_base64_data_to_redis(result_image)
            redis_keys_list.append(s3_url)
            result_images_s3_urls.append(s3_url)

        # Pass on result images references and seeds for post processing
        callback_payload["result_images"] = result_images_s3_urls
        callback_payload["all_seeds"] = all_seeds_list

        set_redis_keys_tracking_key(job_id=job_id,redis_keys_list=redis_keys_list)

    except Exception as e:
        callback_payload["result_images"] = None
        logger.error(e, exc_info=True)

    finally:
        amqp.publish(
            config.EXCHANGE_NAME,
            callback_routing_key,
            callback_payload,
            None,
            callback_priority,
        )
        logger.info(f"Published to callback queue {callback_routing_key}")
