#!/bin/bash
START_PROXY_WORKER=${START_PROXY_WORKER:=false}

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

CODEFORMER_MODEL_PATH="/stable-diffusion-webui/repositories/CodeFormer/weights/"
MOUNT_CODEFORMER_MODEL_PATH="/mnt/data/docker/sd-webui-codeformer-models"

# Just in case there are pipelines outside our control that stubbornly downloads model using huggingface
HF_HOME="/hf-home"  # this is already the default in the docker container but is also an ENV
MOUNT_HF_HOME="/mnt/data/docker/sd-webui-hf-home"
SD_VERSION=${SD_VERSION:="SDXL"}

# Make local mount dirs if they don't exist
mkdir -p ${MOUNT_MAIN_MODELS_PATH}
mkdir -p ${MOUNT_CONTROLNET_EXTENSION_MODELS_PATH}
mkdir -p ${MOUNT_CODEFORMER_MODEL_PATH}

# Run with network host, gpu, and mount points
docker run --rm -t -d \
    --network host \
    --gpus all \
    -e SD_VERSION=${SD_VERSION} \
    -v ${MOUNT_HF_HOME}:${HF_HOME} \
    -v ${MOUNT_MAIN_MODELS_PATH}:${MAIN_MODELS_PATH} \
    -v ${MOUNT_CONTROLNET_EXTENSION_MODELS_PATH}:${CONTROLNET_EXTENSION_MODELS_PATH} \
    -v ${MOUNT_CODEFORMER_MODEL_PATH}:${CODEFORMER_MODEL_PATH} \
    ${DOCKER_IMAGE_NAME}