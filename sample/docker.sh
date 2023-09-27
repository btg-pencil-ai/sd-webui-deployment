#!/bin/bash

# build docker image first in ./sd-webui-deployment dir (docker build -t sd-webui-deployment:latest .)
DOCKER_IMAGE_NAME="sd-webui-deployment:latest"

# Leave this fixed
MAIN_MODELS_PATH="/stable-diffusion-webui/models"
# Configure the below to point to local mountpoint
MOUNT_MAIN_MODELS_PATH="/mnt/data/docker/sd-webui-models"

# Leave this fixed
CONTROLNET_EXTENSION_MODELS_PATH="/stable-diffusion-webui/extensions/sd-webui-controlnet/models"
# Configure the below to point to local mountpoint
MOUNT_CONTROLNET_EXTENSION_MODELS_PATH="/mnt/data/docker/sd-webui-controlnet-models"

# Make local mount dirs if they don't exist
mkdir -p ${MOUNT_MAIN_MODELS_PATH}
mkdir -p ${MOUNT_CONTROLNET_EXTENSION_MODELS_PATH}

# Run with network host, gpu, and mount points
docker run --rm -it \
    --network host \
    --gpus all \
    -v ${MOUNT_MAIN_MODELS_PATH}:${MAIN_MODELS_PATH} \
    -v ${MOUNT_CONTROLNET_EXTENSION_MODELS_PATH}:${CONTROLNET_EXTENSION_MODELS_PATH} \
    ${DOCKER_IMAGE_NAME} \
    /bin/bash