import os
import logging
import requests
from tqdm import tqdm


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAIN_MODELS_PATH = os.environ.get(
    "MAIN_MODELS_PATH", "/stable-diffusion-webui/models")
CONTROLNET_EXTENSION_PATH = os.environ.get(
    "CONTROLNET_EXTENSION_PATH", "/stable-diffusion-webui/extensions/sd-webui-controlnet")

STABLE_DIFFUSION_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "Stable-diffusion")
VAE_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "VAE")
CONTROLNET_MODELS_PATH = os.path.join(CONTROLNET_EXTENSION_PATH, "models")
CONTROLNET_ANNOTATORS_PATH = os.path.join(CONTROLNET_EXTENSION_PATH, "annotator/downloads/clip_vision")
ESRGAN_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "ESRGAN")
REALESRGAN_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "RealESRGAN")
CODEFORMER_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "Codeformer")
CLIP_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "BLIP")

API_TIMEOUT = 300


class ModelDownloader():
    def __init__(self) -> None:
        logger.info("Initialising Model Downloader")

        os.makedirs(MAIN_MODELS_PATH, exist_ok=True)
        os.makedirs(VAE_MODELS_PATH, exist_ok=True)
        os.makedirs(CONTROLNET_EXTENSION_PATH, exist_ok=True)
        os.makedirs(CONTROLNET_MODELS_PATH, exist_ok=True)
        os.makedirs(CONTROLNET_ANNOTATORS_PATH, exist_ok=True)
        os.makedirs(STABLE_DIFFUSION_MODELS_PATH, exist_ok=True)
        os.makedirs(ESRGAN_MODELS_PATH, exist_ok=True)
        os.makedirs(REALESRGAN_MODELS_PATH, exist_ok=True)
        os.makedirs(CODEFORMER_MODELS_PATH, exist_ok=True)
        os.makedirs(CLIP_MODELS_PATH, exist_ok=True)

    def __download_model_from_url__(self, model):
        filename = model.get('filename')
        url = model.get('url')
        target_path = os.path.join(model.get('filepath'), filename)

        if not os.path.exists(target_path):
            try:
                response = requests.head(url, timeout=API_TIMEOUT)
                response.raise_for_status()
                file_size = int(response.headers.get('content-length', 0))

                with requests.get(url, stream=True, timeout=API_TIMEOUT) as r:
                    r.raise_for_status()
                    with open(target_path, 'wb') as file, tqdm(
                        total=file_size, unit='B',
                        unit_scale=True,
                        desc=filename
                    ) as progress_bar:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
                                progress_bar.update(len(chunk))

                logger.info(f"{filename} downloaded successfully")
            except requests.RequestException as e:
                logger.exception(f"An error occurred while downloading {filename}: {e}")
        else:
            logger.info(f"{filename} already exists in the local directory, skipping download.")

    def download_models(self, models_to_download_from_url):
        logger.info("Starting download of models from URL")
        for model in models_to_download_from_url:
            self.__download_model_from_url__(model)


models_to_download = [
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/sd_xl_base_1.0.safetensors',
        'filename': 'sd_xl_base_1.0.safetensors',
        'filepath': STABLE_DIFFUSION_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/sdxl_vae.safetensors',
        'filename': 'sdxl_vae.safetensors',
        'filepath': VAE_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/diffusers_xl_canny_full.safetensors',
        'filename': 'diffusers_xl_canny_full.safetensors',
        'filepath': CONTROLNET_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/ip-adapter-plus_sdxl_vit-h.safetensors',
        'filename': 'ip-adapter-plus_sdxl_vit-h.safetensors',
        'filepath': CONTROLNET_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/clip_h.pth',
        'filename': 'clip_h.pth',
        'filepath': CONTROLNET_ANNOTATORS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/ESRGAN_4x.pth',
        'filename': 'ESRGAN_4x.pth',
        'filepath': ESRGAN_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/RealESRGAN_x4plus.pth',
        'filename': 'RealESRGAN_x4plus.pth',
        'filepath': REALESRGAN_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/RealESRGAN_x2plus.pth',
        'filename': 'RealESRGAN_x2plus.pth',
        'filepath': ESRGAN_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/codeformer-v0.1.0.pth',
        'filename': 'codeformer-v0.1.0.pth',
        'filepath': CODEFORMER_MODELS_PATH
    },
    {
        'url': 'https://storage.googleapis.com/pencil-stg-bl-sd-models/model_base_caption_capfilt_large.pth',
        'filename': 'model_base_caption_capfilt_large.pth',
        'filepath': CLIP_MODELS_PATH
    }
]

ModelDownloader().download_models(models_to_download)
