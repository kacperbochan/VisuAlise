# models.py
from pydantic import BaseModel
from typing import Optional

class Project(BaseModel):
    name: str
    last_opened: Optional[str] = None
    path: Optional[str] = None
