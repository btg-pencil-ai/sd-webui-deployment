FROM  louistrypencil/stable-diffusion-webui:base

# For TCMalloc
RUN apt update \
    && apt install google-perftools -y \
    && rm -rf /var/lib/apt/lists/*

COPY . /sd-webui-deployment
WORKDIR /sd-webui-deployment

CMD ["/bin/bash", "launch.sh"]
