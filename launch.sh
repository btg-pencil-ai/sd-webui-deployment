#!/bin/bash
START_PROXY_WORKER=${START_PROXY_WORKER:=false}

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
    --listen \
    --timeout-keep-alive 300 \
    --port 7860 &

# TODO - supposed to expose v1/server-kill, server-restart, server-stop
# --api-server-stop
if ${START_PROXY_WORKER}; then
    echo "Launching Proxy Worker"
    python3 worker.py &
fi

wait -n

# Exit with status of process that exited first
exit $?