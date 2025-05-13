FROM europe-docker.pkg.dev/productionapplication/pencil-prd-remote-docker-hub/sandratrypencil/stable-diffusion-webui:nvidia-cuda-12.2.0-runtime-ubuntu22.04-v5

# Create a non-root user
RUN groupadd -g 999 pencil && \
    useradd -u 999 -g pencil
WORKDIR /app
# Ensure the user has recursive permissions on all folders under /app
RUN mkdir -p /app /resources && chown -R pencil:pencil /app /resources && \
    chmod -R u+rwx /app /resources

ENV HF_HOME "/hf-home"
ENV CONDA_DIR /opt/conda
ENV PATH=${PATH}:${CONDA_DIR}/bin

# For TCMalloc
RUN apt update \
    && apt install google-perftools wget -y \
    && rm -rf /var/lib/apt/lists/*

RUN pip install xformers==0.0.22 accelerate==0.21.0

# Set HF_HOME just in case there are spurious pipelines outside our control that
# use huggingface to download models - this ensures huggingface cache will download
# to a folder within our control (that we can make persistent) and not ${HOME}/.cache
RUN mkdir -p /hf-home


# Copy project files after setting permissions
COPY --chown=pencil:pencil . /app

RUN pip install -r requirements.txt

RUN chmod +x ./launch.sh

# For worker - we are limited to python <3.10 due to old pika version limited by amqp.py
# implementation - use conda to easily create python3.8 env (3.8 is used in idea-builder)

RUN command -v conda || (wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
	/bin/bash ~/miniconda.sh -b -p /opt/conda)

# Create worker environment 'worker'
# RUN conda env list | grep -q 'worker' || (conda env create -f worker_environment.yml)

# Remove existing worker environment if it exists - this is to reflect any new changes to worker-environment.yml
RUN conda env remove -n worker -y

# Create the worker environment
RUN conda env create -f worker_environment.yml
RUN chown -R pencil:pencil /app && chmod -R u+rwx /app

# Switch to non-root user
USER pencil
#CMD ["/bin/bash", "launch.sh"]
