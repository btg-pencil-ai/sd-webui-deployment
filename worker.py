#!/usr/bin/env python3
import argparse
import os

import src.config as config

from threading import Thread

from src.common.amqp import QueueConsumer, configure_queue
from src.common.logger import get_logger
from src.common.utils import sanitize_params_for_print
from src.sd_webui_proxy.sdwebui_post_callback import sd_webui_post_callback_processor
from src.sd_webui_proxy.util import check_server_readiness


logger = get_logger(__name__)


message_processor = None
worker_name = None
worker_info = {
    'sd_webui_worker_sd15': {
        'message_processor': sd_webui_post_callback_processor,
        'queue': os.environ.get('SD_WEBUI_WORKER_QUEUE', "sd_webui_sd15_queue"),
        'routing_key': os.environ.get('SD15_WEBUI_WORKER_ROUTING_KEY', "*.sd15_webui.worker")
    },
    'sd_webui_worker_sdxl': {
        'message_processor': sd_webui_post_callback_processor,
        'queue': os.environ.get('SD_WEBUI_WORKER_QUEUE', "sd_webui_sdxl_queue"),
        'routing_key': os.environ.get('SDXL_WEBUI_WORKER_ROUTING_KEY', "*.sdxl_webui.worker")
    }
}


parser = argparse.ArgumentParser(description='SD WebUI Worker')
parser.add_argument('-w', '--worker', required=False, choices=worker_info.keys())


def callback(params):
    if 'queue_consumer' not in params.keys():
        raise RuntimeError(
            'Cannot continue as params does not contain queue_consumer instance')
    
    if 'basic_deliver' not in params.keys():
        raise RuntimeError(
            'Cannot continue as params does not contain basic_deliver')
    
    if params['queue_consumer'] is None:
        raise RuntimeError('queue_consumer is None!!!.')

    th = Thread(target=message_consumer, kwargs={'params': params}, daemon=False)
    th.start()


def message_consumer(params):
    queue_consumer = params['queue_consumer']
    basic_deliver = params['basic_deliver']

    try:
        process_message(params)

    except Exception as e:
        logger.error(f'Dropping message! E:{e}')

    finally:
        queue_consumer.add_callback_threadsafe(basic_deliver)


def process_message(params):
    global message_processor

    logger.info('Received message:')

    logger.info(f"{sanitize_params_for_print(params, hide_jwt=True, hide_list=True)}")
    params = {k: v for k, v in params.items() if k not in ['queue_consumer', 'basic_deliver']}

    try:
        if callable(message_processor):
            message_processor(params)

        else:
            raise RuntimeError(
                'Message processor not callable. Cannot process message!!!!')

    except Exception as e:
        logger.error(
            f'Error in worker:{worker_name} message: E: {e}', exc_info=True)
        logger.info(f"{sanitize_params_for_print(params, hide_jwt=True, hide_list=True)}")

        raise


def main():
    if len(worker_info) == 0:
        logger.info("No workers to spin up. Exiting...")
        exit(0)

    global message_processor
    global worker_name

    args = vars(parser.parse_args())
    worker_name = args.get('worker', None)

    if worker_name is None:
        worker_name = os.environ.get('WORKER_NAME', None)
        assert worker_name is not None, "worker_name not provided"

    logger.info('--- Starting {} ---'.format(worker_name))

    priority = 255

    message_processor = worker_info[worker_name]['message_processor']

    logger.info(f"Binding {worker_name} to exchange: {config.EXCHANGE_NAME}")
    configure_queue(config.RABBIT_URL,
                    config.EXCHANGE_NAME,
                    worker_info[worker_name]['queue'],
                    worker_info[worker_name]['routing_key'],
                    priority=priority)

    if worker_info[worker_name].get('bind_to_delay_exchange', False) is True:
        if config.ENABLE_REQUEUE is True:
            logger.info(
                f"Also binding {worker_name} to delay exchange: {config.DELAY_EXCHANGE_NAME}")
            configure_queue(config.RABBIT_URL,
                            config.DELAY_EXCHANGE_NAME,
                            worker_info[worker_name]['queue'],
                            worker_info[worker_name]['routing_key'],
                            priority=priority,
                            exchange_type='x-delayed-message')

        else:
            logger.warning(f"ENABLE_REQUEUE=False - not binding {worker_name} "
                           f"to delay exchange: {config.DELAY_EXCHANGE_NAME}")

    consumer = QueueConsumer(
        config.RABBIT_URL, worker_info[worker_name]['queue'], callback)

    try:
        # Let this raise - we should not accept messages if we fail basic checks
        check_server_readiness()
        logger.info(f"Server is ready - starting consumer & connecting to queue")

        consumer.run()

    except KeyboardInterrupt:
        logger.info(f'\nExiting Worker')
        consumer.stop()
        consumer.close_connection()
        logger.info('Bye!!!')


if __name__ == '__main__':
    main()
