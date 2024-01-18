import os
import logging

from huggingface_hub import hf_hub_download


logging.basicConfig(level = logging.INFO)


MAIN_MODELS_PATH=os.environ.get("MAIN_MODELS_PATH", 
                                "/stable-diffusion-webui/models")
CONTROLNET_EXTENSION_MODELS_PATH=os.environ.get("CONTROLNET_EXTENSION_MODELS_PATH", 
                                                "/stable-diffusion-webui/extensions/sd-webui-controlnet/models")
ANNOTATOR_MODELS_PATH=os.environ.get("ANNOTATOR_MODELS_PATH", 
                                                "/stable-diffusion-webui/extensions/sd-webui-controlnet/annotator/downloads/clip_vision")

logger = logging.getLogger(__name__)

STABLE_DIFFUSION_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "Stable-diffusion")
VAE_MODELS_PATH = os.path.join(MAIN_MODELS_PATH, "VAE")

class HuggingFaceModelDownloader():
    def __init__(self) -> None:
        logger.info("Starting Hugging Face Model Downloader")

        # Ensure directories exist or create them
        os.makedirs(MAIN_MODELS_PATH, exist_ok=True)
        os.makedirs(CONTROLNET_EXTENSION_MODELS_PATH, exist_ok=True)

        models_to_download = [
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
        ]
        
        for model in models_to_download:
            self.download_model(model)
    
    def download_model(self, model):
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
                logger.error(f"Failed to download {filename}: {e}")
        else:
            logger.info(f"{filename} already exists in the local directory, skipping download.")

cls = HuggingFaceModelDownloader()
