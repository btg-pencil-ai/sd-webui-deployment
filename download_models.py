import os
import sys

MAIN_MODELS_PATH=os.environ.get("MAIN_MODELS_PATH", 
                                "/stable-diffusion-webui/models")
CONTROLNET_EXTENSION_MODELS_PATH=os.environ.get("CONTROLNET_EXTENSION_MODELS_PATH", 
                                                "/stable-diffusion-webui/extensions/sd-webui-controlnet/models")

raise NotImplementedError("Need to implement this")