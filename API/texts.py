import json
import os
import datetime
from fastapi import APIRouter, Body, FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import tiktoken
from models.models import Project, ProjectMenuData, LLM, DiffusionModel
from models.dto_models import StoryElementMiniDTO
from settings import global_settings as settings, load_user_settings
from typing import List, Optional
from pathlib import Path
from API.project import  get_project_by_name, get_text_data, new_split_text_by_tokens

router = APIRouter()
templates = Jinja2Templates(directory="templates/project")
projects_file = "projects.json"
@router.get("")
async def get_text(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    text_file = get_text_data(project_path)

    if text_file:
        with open(text_file, 'r', encoding='utf-8') as file:
            text = file.read()
            return {"text": text}
    else:
        return {"text": ""}

