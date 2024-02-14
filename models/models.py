# models.py
from pydantic import BaseModel
from typing import Optional


class LLM(BaseModel):
    model: str
    temperature: float
    top_k: int
    top_p: float
    repetition_penalty: float
    max_length: int
    device: str = "gpu"

class DiffusionModel(BaseModel):
    model: str
    steps: int
    temperature: float = 0.7
    batch: int
    device: str = "gpu"

class GeneratedImageData(BaseModel):
    model: str
    steps: int
    seed: str
    temperature: float
    prompt: str

class Image(BaseModel):
    path: str
    generatedImageData: Optional[GeneratedImageData] = None

class StoryElementVersion(BaseModel):
    user_name: str
    user_notes: Optional[str] = None
    description: Optional[str] = None
    image: Optional[Image]

class StoryMention(BaseModel):
    story_fragment_id: str
    story_element_id: int
    description: str

class StoryElement(BaseModel):
    id: int
    name: str
    user_name: str
    user_notes: Optional[str] = None
    description: Optional[str] = None
    mention_n: int # Number of times this element is mentioned in the story
    storyElements: Optional[list[StoryMention]] = []
    type: str # "character" or "location"
    versions: list[StoryElementVersion] = []

class TextChunk(BaseModel):
    id: int
    text: str
    
    storyElements: list[StoryMention] = []

class Text(BaseModel):
    id: int
    text: str
    user_name: str
    user_notes: Optional[str] = None
    
    storyElements: list[StoryMention] = []
    chunks: list[str]

class ProgramSettings(BaseModel):
    projects_dir: str
    llm_dir: str
    diffusion_dir: str
    
    default_llm: LLM
    default_diffusion_model: DiffusionModel

class ProjectMenuData(BaseModel):
    name: str
    last_opened: str
    path: str

class Project(BaseModel):
    name: str
    characters_n :int
    locations_n :int
    llm: LLM
    diffusion_model: DiffusionModel