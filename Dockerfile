FROM  louistrypencil/stable-diffusion-webui:nvidia-cuda-12.2.0-runtime-ubuntu22.04-v2

# For TCMalloc
RUN apt update \
    && apt install google-perftools -y \
    && rm -rf /var/lib/apt/lists/*

RUN pip install xformers accelerate

# Set HF_HOME just in case there are spurious pipelines outside our control that
# use huggingface to download models - this ensures huggingface cache will download
# to a folder within our control (that we can make persistent) and not ${HOME}/.cache
RUN mkdir /hf-home
ENV HF_HOME "/hf-home"

COPY . /sd-webui-deployment
WORKDIR /sd-webui-deployment

CMD ["/bin/bash", "launch.sh"]
