import os
import boto3
import uuid
import mimetypes
from src.common.constants import R2Mapping
from src.config import R2_ENABLED

from src.common.logger import get_logger

logger = get_logger(__name__)

def get_file_extension(filename:str)->str:
    return os.path.splitext(filename)[1]

class AWS(object):
    __shared_state = {}
    __aws_inited = False

    def __init__(self):
        self.__dict__ = self.__shared_state
        if self.__aws_inited is False:
            self.__aws_inited = True
            logger.info("Loading AWS session as __session is None")
            self.__session = self.__get_session()
            logger.info("Loading AWS session done")

    def __get_key_secret_region(self, region=None):
        key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
        if region is None:
            region = os.environ.get("AWS_REGION")

        if not key or not secret:
            logger.error("AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not found in environment")
            raise RuntimeError("AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not found in environment")
        return key, secret, region

    @staticmethod
    def __get_session():
        session = boto3.Session()
        return session

    def clear_session(self):
        logger.info("Clearing AWS session")
        self.__aws_inited = False
        self.__session = None

    def get_session(self):
        if self.__session is None:
            self.__session = self.__get_session()
        return self.__session

    def get_s3_client(self, region=None):
        if self.__session is None:
            self.__session = self.__get_session()

        if os.environ.get('IN_LAMBDA', 'false') == 'true':
            logger.info('IN_LAMBDA')

            return self.__session.client("s3")

        key, secret, region = self.__get_key_secret_region(region=region)
        return self.__session.client("s3", aws_access_key_id=key, aws_secret_access_key=secret, region_name=region)

    def get_s3_resource(self):
        if self.__session is None:
            self.__session = self.__get_session()

        key, secret, region = self.__get_key_secret_region()
        return self.__session.resource("s3", aws_access_key_id=key, aws_secret_access_key=secret, region_name=region)
    
def get_aws_session():
    return AWS().get_session()


def get_s3_client():
    return AWS().get_s3_client()


def get_s3_resource():
    return AWS().get_s3_resource()

def upload_to_s3(filename, bucket, key=None, public=False):
    s3 = get_s3_client()
    if not os.path.exists(filename):
        raise FileNotFoundError(filename)
    content_type = mimetypes.MimeTypes().guess_type(filename)[0]
    if key is None:
        key = str(uuid.uuid4()) + get_file_extension(filename)
    extra_args = {}
    if content_type is not None:
        extra_args["ContentType"] = content_type
    if public is True:
        extra_args["ACL"] = "public-read"
    s3.upload_file(filename, bucket, key, ExtraArgs=extra_args)
    logger.debug("Uploaded %s to %s with key: %s", filename, bucket, key)
    return key

def s3_public_url(bucket: str, key: str) -> str:
    if R2_ENABLED is True:
        cloudfront_url = R2Mapping[bucket]
        return f"https://{cloudfront_url}/{key}"
    else:
        return f"https://{bucket}.s3.amazonaws.com/{key}"
