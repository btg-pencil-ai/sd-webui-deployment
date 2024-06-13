import os
import logging
import requests
import re
from tqdm import tqdm
import boto3

from huggingface_hub import hf_hub_download


logging.basicConfig(level = logging.INFO)


MAIN_MODELS_PATH=os.environ.get("MAIN_MODELS_PATH",
                                "/stable-diffusion-webui/models")
CONTROLNET_EXTENSION_MODELS_PATH=os.environ.get("CONTROLNET_EXTENSION_MODELS_PATH",
                                                "/stable-diffusion-webui/extensions/sd-webui-controlnet/models")
ANNOTATOR_MODELS_PATH=os.environ.get("ANNOTATOR_MODELS_PATH",
                                                "/stable-diffusion-webui/extensions/sd-webui-controlnet/annotator/downloads/clip_vision")
EMBEDDINGS_PATH=os.environ.get("EMBEDDINGS_PATH",
                               "/stable-diffusion-webui/embeddings")

CIVIT_AI_MODELS_ENDPOINT = os.environ.get("CIVIT_AI_MODELS_ENDPOINT",
                                          "https://civitai.com/api/v1/models/")

AWS_ACCESS_KEY_ID=os.environ.get("AWS_ACCESS_KEY_ID",
                                 "dummy-id")
AWS_SECRET_ACCESS_KEY=os.environ.get("AWS_SECRET_ACCESS_KEY",
                                     "dummy-key")
AWS_S3_BUCKET=os.environ.get("AWS_S3_BUCKET",
                             "dummy-bucket")

logger = logging.getLogger(__name__)

STABLE_DIFFUSION_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "Stable-diffusion")
VAE_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "VAE")
LORA_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "Lora")
SWINIR_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "SwinIR")

API_TIMEOUT = 300

class ModelDownloader():
    def __init__(self) -> None:
        logger.info("Starting Model Downloader")

        # Ensure directories exist or create them
        os.makedirs(MAIN_MODELS_PATH, exist_ok=True)
        os.makedirs(CONTROLNET_EXTENSION_MODELS_PATH, exist_ok=True)
        os.makedirs(ANNOTATOR_MODELS_PATH, exist_ok=True)
        os.makedirs(EMBEDDINGS_PATH, exist_ok=True)
        os.makedirs(STABLE_DIFFUSION_MODELS_PATH, exist_ok=True)
        os.makedirs(VAE_MODELS_PATH, exist_ok=True)
        os.makedirs(LORA_MODELS_PATH, exist_ok=True)
        os.makedirs(SWINIR_MODELS_PATH, exist_ok=True)

        hugging_face_models_to_download = [
            {'repo_id': 'stabilityai/stable-diffusion-xl-base-1.0', 'filename': 'sd_xl_base_1.0.safetensors', 'filepath': STABLE_DIFFUSION_MODELS_PATH},
            {'repo_id': 'stabilityai/stable-diffusion-xl-refiner-1.0', 'filename': 'sd_xl_refiner_1.0.safetensors', 'filepath': STABLE_DIFFUSION_MODELS_PATH},
            {'repo_id': 'stabilityai/sdxl-vae', 'filename': 'sdxl_vae.safetensors', 'filepath': VAE_MODELS_PATH},
            {'repo_id': 'stabilityai/sd-vae-ft-mse-original', 'filename': 'vae-ft-mse-840000-ema-pruned.ckpt', 'filepath': VAE_MODELS_PATH},
            {'repo_id': 'lllyasviel/sd_control_collection', 'filename': 'diffusers_xl_canny_full.safetensors', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/sd_control_collection', 'filename': 'sai_xl_depth_256lora.safetensors', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'runwayml/stable-diffusion-v1-5', 'filename': 'v1-5-pruned-emaonly.safetensors', 'filepath': STABLE_DIFFUSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/ControlNet-v1-1', 'filename': 'control_v11p_sd15_canny.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/ControlNet-v1-1', 'filename': 'control_v11f1p_sd15_depth.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/ControlNet-v1-1', 'filename': 'control_v11e_sd15_shuffle.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/sd_control_collection', 'filename': 'ip-adapter_xl.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/Annotators', 'filename': 'clip_g.pth', 'filepath': ANNOTATOR_MODELS_PATH},
            {'repo_id': 'runwayml/stable-diffusion-inpainting', 'filename': 'sd-v1-5-inpainting.ckpt', 'filepath': STABLE_DIFFUSION_MODELS_PATH},
            {'repo_id': 'stabilityai/control-lora', 'filename': 'control-LoRAs-rank256/control-lora-canny-rank256.safetensors', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/sd-controlnet-scribble', 'filename': 'diffusion_pytorch_model.safetensors', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/ControlNet', 'filename': 'models/control_sd15_hed.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/sd_control_collection', 'filename': 'ip-adapter_sd15.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'TencentARC/T2I-Adapter', 'filename': 'models_XL/adapter-xl-sketch.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
            {'repo_id': 'stabilityai/stable-diffusion-2-1-unclip', 'filename': 'sd21-unclip-h.ckpt', 'filepath': STABLE_DIFFUSION_MODELS_PATH},
            {'repo_id': 'lllyasviel/ControlNet-v1-1', 'filename': 'control_v11f1e_sd15_tile.pth', 'filepath': CONTROLNET_EXTENSION_MODELS_PATH},
        ]

        civit_ai_models_to_download = [
            {'model_url': 'https://civitai.com/models/46422/juggernaut', 'filename': 'juggernaut-reborn.safetensors', 'filepath': STABLE_DIFFUSION_MODELS_PATH},
            {'model_url': 'https://civitai.com/models/58390/detail-tweaker-lora-lora', 'filename': 'add_detail.safetensors', 'filepath': LORA_MODELS_PATH},
            {'model_url': 'https://civitai.com/models/82098/add-more-details-detail-enhancer-tweaker-lora', 'filename': 'more_details.safetensors', 'filepath': LORA_MODELS_PATH},
            {'model_url': 'https://civitai.com/models/81563/juggernaut-negative-embedding', 'filename': 'JuggernautNegative-neg.pt', 'filepath': EMBEDDINGS_PATH},
        ]

        s3_models_to_download = [
            {'s3_key': 'SDXLrender_v2.0.safetensors', 'filepath': LORA_MODELS_PATH},
            {'s3_key': 'SwinIR_4x.pth', 'filepath': SWINIR_MODELS_PATH},
        ]

        self.s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        self.s3_bucket = AWS_S3_BUCKET

        logger.info("Starting download of Hugging Face models")
        for model in hugging_face_models_to_download:
            self.download_hugging_face_model(model)

        logger.info("Starting download of Civit AI models")
        for model in civit_ai_models_to_download:
            self.download_civit_ai_model(model)

        logger.info("Starting download of S3 models")
        for model in s3_models_to_download:
            self.download_s3_model(model)

    def download_hugging_face_model(self, model):
        repo_id = model['repo_id']
        filename = model['filename']
        target_path = os.path.join(model['filepath'], filename)

        # Check if the file already exists in the local directory
        if not os.path.exists(target_path):
            try:
                hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=model['filepath'],
                    local_dir_use_symlinks=False  # see https://github.com/huggingface/diffusers/issues/2886 
                )
                logger.info(f"{filename} downloaded successfully")
            except Exception as e:
                logger.exception(f"An unexpected error occurred while downloading {filename}: {e}")
        else:
            logger.info(f"{filename} already exists in the local directory, skipping download.")

    def download_civit_ai_model(self, model):
        filename = model['filename']
        target_path = os.path.join(model['filepath'], filename)

        # Check if the file already exists in the local directory
        if not os.path.exists(target_path):
            try:
                model_id_match = re.search(r'models/(\d+)', model['model_url'])
                assert model_id_match, f"Invalid URL format for model ID: {model['model_url']}"
                endpoint = CIVIT_AI_MODELS_ENDPOINT + model_id_match.group(1)

                # Get model data from Civit AI model api
                response = requests.get(endpoint, timeout=API_TIMEOUT)
                response.raise_for_status()
                data = response.json()

                # Get model version and download URL from model data
                model_version_id_match = re.search(r'modelVersionId=(\d+)', model['model_url'])
                download_url = None
                if model_version_id_match:
                    model_version_id = int(model_version_id_match.group(1))
                    for model_version in data.get('modelVersions', []):
                        if model_version['id'] == model_version_id:
                            download_url = model_version.get('downloadUrl')
                            break
                    assert download_url, "Model version ID not found in model data"
                else:
                    download_url = data.get('modelVersions', [{}])[0].get('downloadUrl')
                assert download_url, "Download URL not found"

                # Download model from Civit AI
                with requests.get(download_url, stream=True, timeout=API_TIMEOUT) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))

                    with open(target_path, 'wb') as file, tqdm(
                        total=total_size, unit='B', unit_scale=True, desc=filename
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                file.write(chunk)
                                pbar.update(len(chunk))
                logger.info(f"{filename} downloaded successfully")
            except Exception as e:
                logger.exception(f"An unexpected error occurred while downloading {filename}: {e}")
        else:
            logger.info(f"{filename} already exists in the local directory, skipping download.")

    def download_s3_model(self, model):
        filename = model['s3_key']
        target_path = os.path.join(model['filepath'], filename)

        # Check if the file already exists in the local directory
        if not os.path.exists(target_path):
            try:
                file_size = self.s3_client.head_object(Bucket=self.s3_bucket, Key=filename)['ContentLength']
                progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=filename)

                def progress_hook(bytes_amount):
                    progress_bar.update(bytes_amount)

                # Download model from S3 bucket
                self.s3_client.download_file(self.s3_bucket, filename, target_path, Callback=progress_hook)
                progress_bar.close()
                logger.info(f"{filename} downloaded successfully")
            except Exception as e:
                logger.exception(f"An unexpected error occurred while downloading {filename}: {e}")
        else:
            logger.info(f"{filename} already exists in the local directory, skipping download.")

cls = ModelDownloader()
