#!/bin/bash

MAIN_MODELS_PATH=${MAIN_MODELS_PATH:="/stable-diffusion-webui/models"}

# If we mount a fresh disk we might be missing these subdirs during the 1st run, so recreate them here
for IFOLDER in Codeformer  ControlNet  ESRGAN  GFPGAN  LDSR  Lora  Stable-diffusion  SwinIR  VAE  VAE-approx  deepbooru  hypernetworks  karlo; do
    mkdir -p ${MAIN_MODELS_PATH}/${IFOLDER}
done

# Run any prep scripts to check & download models here - feel free to use env vars to parametrize paths
# Please check if sdwebui already has functions to auto-download models if not present, if they do then we don't need to do it
python3 download_models.py

# Run and listen to port in API mode
cd /stable-diffusion-webui
LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4" python3 launch.py \
    --xformers \
    --no-half-vae \
    --skip-prepare-environment \
    --skip-install \
    --no-download-sd-model \
    --medvram \
    --medvram-sdxl \
    --api \
    --listen

# TODO - supposed to expose v1/server-kill, server-restart, server-stop
# --api-server-stop