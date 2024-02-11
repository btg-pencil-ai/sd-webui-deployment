from dataclasses import dataclass
from typing import List, Union
@dataclass
class BatchImagesListType:
    name:str
    data:str

@dataclass
class UpscaleBatchImagesListPayload:
    imageList:List[BatchImagesListType]

@dataclass
class ControlNetArgs:
    input_image: str

@dataclass
class ControlNet:
    args: List[ControlNetArgs]

@dataclass
class AlwaysOnScripts:
    controlnet: ControlNet

@dataclass
class Img2ImgPayload:
    alwayson_scripts: AlwaysOnScripts
    init_images: List[str]
    mask: Union[str, None]

@dataclass
class SDLamaCleanerPayload:
    input_image:str

SDWebUIPayload = Union[Img2ImgPayload, SDLamaCleanerPayload]
    