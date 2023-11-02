from dataclasses import dataclass
from typing import List
@dataclass
class BatchImagesListType:
    name:str
    data:str

@dataclass
class UpscaleBatchImagesListPayload:
    imageList:List[BatchImagesListType]