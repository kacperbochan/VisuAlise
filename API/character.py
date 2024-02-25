import json
import os
import datetime
from fastapi import APIRouter, Body, FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from models.models import Project, ProjectMenuData, LLM, DiffusionModel
from models.dto_models import StoryElementMiniDTO
from settings import global_settings as settings, load_user_settings
from typing import List, Optional
from pathlib import Path
from API.project import get_project_by_name, get_story_object_data, get_visual_settings

router = APIRouter()
templates = Jinja2Templates(directory="templates/project")


@router.get("")
async def read_character(request: Request, project_name: str, character_id: str):
    
    Url: str = "/project/"+project_name+"/character/"+character_id+"/info"
    
    return RedirectResponse(url=Url, status_code=302)
    



@router.get("/info", response_class=HTMLResponse)
async def read_character_info(request: Request, project_name: str, character_id: str):
    
    project, project_path = get_project_by_name(project_name)
    character = get_story_object_data(project, project_path, character_id, False)
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("character/character_info.html", {
        "request": request,
        "project": project,
        "sub_page": "info",
        **character,
        **visual_settings
    })

@router.get("/gallery", response_class=HTMLResponse)
async def read_character(request: Request, project_name: str, character_id: str, page: Optional[int] = Query(1, alias="page")):
    
    if(page < 1):
        page=0
    else:
        page -= 1
    
    
    project, project_path = get_project_by_name(project_name)
    character = get_story_object_data(project, project_path, character_id, False)
    
    page_amount = len(character["images"])//12
    if(len(character["images"])%12 != 0):
        page_amount += 1
    if(page >= page_amount):
        page = page_amount-1
        
    character["images"] = character["images"][page*12:page*12+12]
    
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("character/character_gallery.html", {
        "request": request,
        "project": project,
        "page_amount": page_amount,
        "current_page": page+1,
        "sub_page": "gallery",
        **character,
        **visual_settings
    })

@router.get("/text_data", response_class=HTMLResponse)
async def read_character(request: Request, project_name: str, character_id: str):
    project, project_path = get_project_by_name(project_name)
    character = get_story_object_data(project, project_path, character_id, False)
    visual_settings = get_visual_settings()
    
    text_data = [{"text": """Alice was beginning to get very tired of sitting by her sister on the
                bank, and of having nothing to do: once or twice she had peeped into
                the book her sister was reading, but it had no pictures or
                conversations in it, “and what is the use of a book,” thought Alice
                “without pictures or conversations?”

                So she was considering in her own mind (as well as she could, for the
                hot day made her feel very sleepy and stupid), whether the pleasure of
                making a daisy-chain would be worth the trouble of getting up and
                picking the daisies, when suddenly a White Rabbit with pink eyes ran
                close by her.
                """,
                "data": "white, rabbit, pink eyes"
                },
                {"text": """There was nothing so _very_ remarkable in that; nor did Alice think it
                so _very_ much out of the way to hear the Rabbit say to itself, “Oh
                dear! Oh dear! I shall be late!” (when she thought it over afterwards,
                it occurred to her that she ought to have wondered at this, but at the
                time it all seemed quite natural); but when the Rabbit actually _took a
                watch out of its waistcoat-pocket_, and looked at it, and then hurried
                on, Alice started to her feet, for it flashed across her mind that she
                had never before seen a rabbit with either a waistcoat-pocket, or a
                watch to take out of it, and burning with curiosity, she ran across the
                field after it, and fortunately was just in time to see it pop down a
                large rabbit-hole under the hedge.""", 
                "data": "Alice, sister"}]
    
    return templates.TemplateResponse("character/character_text_data.html", {
        "request": request,
        "project": project,
        "text_data": text_data,
        "sub_page": "text_data",
        **character,
        **visual_settings
    })

@router.get("/versions", response_class=HTMLResponse)
async def read_character(request: Request, project_name: str, character_id: str):
    project, project_path = get_project_by_name(project_name)
    character = get_story_object_data(project, project_path, character_id, False)
    visual_settings = get_visual_settings()
    
    return templates.TemplateResponse("character/character_versions.html", {
        "request": request,
        "project": project,
        "sub_page": "versions",
        **character,
        **visual_settings
    })
