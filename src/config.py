import os

PLATFORM_ENV = os.environ.get('PLATFORM_ENV', 'development').lower()

RABBIT_URL = os.environ.get('RABBIT_URL', 'amqp://guest:guest@localhost:5672?heartbeat=3600')
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_TOKEN = os.environ.get('JWT_TOKEN')
CALLBACK_RABBIT_URL = RABBIT_URL  # in case we want to change this in the future
EXCHANGE_NAME = os.environ.get('EXCHANGE_NAME')

SD_WEBUI_API_ENDPOINT = os.environ.get("SD_WEBUI_API_ENDPOINT", "http://localhost:7860")
BATCH_UPSCALE_ENDPOINT = "sdapi/v1/extra-batch-images/"
SET_SD_WEBUI_OPTIONS_ENDPOINT = "sdapi/v1/options/"

