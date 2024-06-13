import os

PLATFORM_ENV = os.environ.get('PLATFORM_ENV', 'development').lower()
TEST_MODE = PLATFORM_ENV == "test"

RABBIT_URL = os.environ.get('RABBIT_URL', 'amqp://guest:guest@localhost:5672?heartbeat=3600')
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_TOKEN = os.environ.get('JWT_TOKEN')
CALLBACK_RABBIT_URL = RABBIT_URL  # in case we want to change this in the future
EXCHANGE_NAME = os.environ.get('EXCHANGE_NAME',"pencil-exchange")
S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "dummy")

try:
    ENABLE_REQUEUE = os.environ.get('ENABLE_REQUEUE', 'false').lower() == 'true'

except Exception as e:
    ENABLE_REQUEUE = False

DELAY_EXCHANGE_NAME = os.environ.get('DELAY_EXCHANGE_NAME')

SD_WEBUI_API_ENDPOINT = os.environ.get("SD_WEBUI_API_ENDPOINT", "http://localhost:7860")
BATCH_UPSCALE_ENDPOINT = "sdapi/v1/extra-batch-images/"
SET_SD_WEBUI_OPTIONS_ENDPOINT = "sdapi/v1/options/"
SD_WEBUI_INTERROGATE_ENDPOINT = "sdapi/v1/interrogate/"

# Be very aggressive on this so we don't waste time
SERVER_CHECK_INITIAL_DELAY=1
SERVER_CHECK_RETRIES=10
SERVER_CHECK_BACKOFF=1  # factor * 2^num_prev_retries e.g. if 3, will be 3 * (2, 4, 8, ...)
SERVER_CHECK_TIMEOUT=30

SERVER_POST_RETRIES=3
SERVER_POST_BACKOFF=1
SERVER_POST_TIMEOUT=300

###############AWS###############
AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET","pencil-production-bucket")
R2_ENABLED = os.environ.get("R2_ENABLED", "true") == "true"

IMAGE_GENERATION_REDIS_EXPIRE = 3600
IMAGE_GENERATION_REDIS_LOCK_DURATION_SECONDS = 5

