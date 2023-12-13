import src.config as config
from urllib.parse import urljoin

from src.common import amqp
from src.common.logger import get_logger
from src.sd_webui_proxy.sdwebui_post_callback_util import post_request, get_generated_images, get_upscaled_images

logger = get_logger()

def sd_webui_post_callback_processor(params):
    try:
        callback_message = params.get("callback_message", {})

        callback_routing_key = callback_message.get("routing_key", None)
        assert callback_routing_key is not None, "callback_routing_key not provided"

        callback_payload = callback_message.get("payload", None)
        assert callback_payload is not None, "callback payload not provided"

        callback_priority = callback_message.get("callback_priority", 255)

        requests = params.get("requests", [])
        assert requests, "requests is empty"

        sd_webui_options_payload = params.get("sd_webui_options_payload", None)
        upscale_payload = params.get("upscale_payload", None)

        width = callback_payload.get("gen_image_width")
        height = callback_payload.get("gen_image_height")

        if sd_webui_options_payload is not None:
            set_sd_webui_options_full_endpoint = urljoin(
                config.SD_WEBUI_API_ENDPOINT, config.SET_SD_WEBUI_OPTIONS_ENDPOINT
            )
            post_request(url=set_sd_webui_options_full_endpoint,payload=sd_webui_options_payload,)
            logger.info(f"Completed switching models")

        result_images = get_generated_images(requests)

        if upscale_payload is not None:
            upscaled_and_resized_images = get_upscaled_images(upscale_payload=upscale_payload,resize_width=width,resize_height=height,result_images=result_images)
            result_images = list(filter(None, upscaled_and_resized_images))

        callback_payload["base64_images"] = result_images

    except Exception as e:
        callback_payload["base64_images"] = None
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
