#!/bin/bash
MAIN_MODELS_PATH=${MAIN_MODELS_PATH:="/stable-diffusion-webui/models"}

# If we mount a fresh disk we might be missing these subdirs during the 1st run, so recreate them here
for IFOLDER in Codeformer  ControlNet  ESRGAN  GFPGAN  LDSR  Lora  Stable-diffusion  SwinIR  VAE  VAE-approx  deepbooru  hypernetworks  karlo; do
    mkdir -p ${MAIN_MODELS_PATH}/${IFOLDER}
done

# Create HF_HOME that we can mount to persistent volume during deployment. We won't normally use it, but we should have it
# in case there are pipelines outside our control that stubbornly calls huggingface to download models
export HF_HOME=${HF_HOME:="/hf-home"}
mkdir -p ${HF_HOME}

# Run any prep scripts to check & download models here - feel free to use env vars to parametrize paths
# Please check if sdwebui already has functions to auto-download models if not present, if they do then we don't need to do it
python3 download_models.py

git clone https://github.com/ljleb/sd-webui-freeu.git /stable-diffusion-webui/extensions/sd-webui-freeu

# Run and listen to port in API mode
cd /stable-diffusion-webui

if [ ${SD_VERSION} == "SD15" ]; then
    # Append flags for 'SD15'
    LAUNCH_FLAGS="--ckpt ${MAIN_MODELS_PATH}/Stable-diffusion/v1-5-pruned-emaonly.safetensors \
        --vae-path ${MAIN_MODELS_PATH}/VAE/vae-ft-mse-840000-ema-pruned.ckpt \
        --medvram"

elif [ ${SD_VERSION} == "SD15_INPAINT" ]; then
    # Append flags for other cases
    LAUNCH_FLAGS="--ckpt ${MAIN_MODELS_PATH}/Stable-diffusion/sd-v1-5-inpainting.ckpt \
        --vae-path ${MAIN_MODELS_PATH}/VAE/vae-ft-mse-840000-ema-pruned.ckpt \
        --medvram"

elif [ ${SD_VERSION} == "SDXL" ]; then
    # Append flags for other cases
    LAUNCH_FLAGS="--ckpt ${MAIN_MODELS_PATH}/Stable-diffusion/sd_xl_base_1.0.safetensors \
        --vae-path ${MAIN_MODELS_PATH}/VAE/sdxl_vae.safetensors \
        --medvram"

elif [ ${SD_VERSION} == "SD21_UNCLIP" ]; then
    # Append flags for other cases
    LAUNCH_FLAGS="--ckpt ${MAIN_MODELS_PATH}/Stable-diffusion/sd21-unclip-h.ckpt \
        --vae-path ${MAIN_MODELS_PATH}/VAE/vae-ft-mse-840000-ema-pruned.ckpt"

else
    echo "Invalid SD_VERSION ${SD_VERSION}"
    exit 1

fi

echo "SD_VERSION set to ${SD_VERSION} with LAUNCH_FLAGS: ${LAUNCH_FLAGS}"

LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4" python3 launch.py  ${LAUNCH_FLAGS} \
    --controlnet-loglevel DEBUG \
    --xformers \
    --no-half-vae \
    --skip-prepare-environment \
    --skip-install \
    --no-download-sd-model \
    --medvram-sdxl \
    --api \
    --listen \
    --timeout-keep-alive 300 \
    --port 7860
