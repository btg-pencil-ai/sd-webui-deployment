import json
from urllib.parse import urljoin

from src.aws.aws import s3_public_url
import src.config as config
from src.common import amqp
from src.common.logger import get_logger
from src.sd_webui_proxy.constant import AI_MAGIC_TOOLS_REDIS_KEY_PREFIX, GENERATED_IMAGES_S3_BASE_PATH
from src.sd_webui_proxy.util import get_by_redis_key, get_generated_image_s3_key, set_base64_data_to_redis, set_redis_keys_tracking_key, upload_base64_to_s3
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

        client_id = callback_payload.get("client_id")
        batch_uuid = callback_payload.get("batch_uuid")
        job_id = callback_payload.get("job_id")

        redis_key = f"{AI_MAGIC_TOOLS_REDIS_KEY_PREFIX}_{job_id}"
        redis_keys_list = get_by_redis_key(redis_key)
        redis_keys_list = json.loads(redis_keys_list)

        if sd_webui_options_payload is not None:
            set_sd_webui_options_full_endpoint = urljoin(
                config.SD_WEBUI_API_ENDPOINT, config.SET_SD_WEBUI_OPTIONS_ENDPOINT
            )
            post_request(url=set_sd_webui_options_full_endpoint,payload=sd_webui_options_payload,)
            logger.info(f"Completed switching models")

        result_images = []
        for request in requests:
            result_images.extend(get_generated_images(request))

        if upscale_payload is not None:
            upscaled_and_resized_images = get_upscaled_images(upscale_payload=upscale_payload,resize_width=width,resize_height=height,result_images=result_images)
            result_images = list(filter(None, upscaled_and_resized_images))

        # convert to s3 urls
        result_images_s3_urls = []
        for result_image in result_images:
            s3_url = set_base64_data_to_redis(result_image)
            redis_keys_list.append(s3_url)
            # s3_key = get_generated_image_s3_key(
            #     base_filename=GENERATED_IMAGES_S3_BASE_PATH,
            #     client_id=client_id,
            #     batch_uuid=batch_uuid,
            #     image_ext="jpg",
            # )
            # upload_base64_to_s3(result_image, s3_key)
            # s3_url = s3_public_url(config.AWS_S3_BUCKET, s3_key)
            # logger.info(f"Generated image saved to {s3_url}")

            result_images_s3_urls.append(s3_url)

        callback_payload["result_images"] = result_images_s3_urls
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
