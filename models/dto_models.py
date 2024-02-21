from pydantic import BaseModel
from typing import Optional
from models.models import *

class StoryElementVersionDTO(BaseModel):
    user_name: str
    description:str

class StoryElementDTO(BaseModel):
    name: str
    user_name: str
    description: Optional[str] = None
    type: str # "character" or "location"
    versions: list[StoryElementVersionDTO] = []

class StoryElementMiniDTO(BaseModel):
    name: str
    user_name: str
    image: Optional[str] = None
    image_path: Optional[str] = None
    prompt: Optional[str] = None
    description: Optional[str] = None

class PromptBlockDTO(BaseModel):
    type: str
    StoryElement: str
    prompt: str