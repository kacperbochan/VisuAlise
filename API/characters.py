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
from API.project import get_highest_id, get_project_by_name, get_project_story_objects, get_project_story_objects_names, get_visual_settings, get_safe_json, update_project_data, get_project_story_object_info, get_project_story_objects_names, get_free_user_name, check_if_image_exists, check_if_image_is_referenced

router = APIRouter()
templates = Jinja2Templates(directory="templates/project")

@router.get("")
async def read_character(request: Request, project_name: str):
    
    Url: str = "/project/"+project_name+"/characters/list"
    
    return RedirectResponse(url=Url, status_code=302)
    

@router.get("/list")
async def read_character_list(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    visual_settings = get_visual_settings()
    
    characters = get_project_story_objects(project_path, False)
    return templates.TemplateResponse("characters_list/characters_list.html", {
        "request": request,
        "characters": characters,
        "project": project,
        "sub_page": "list",
        **visual_settings
    })

@router.get("/creation")
async def character_creation(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    visual_settings = get_visual_settings()
    
    character_names = get_project_story_objects_names(project_path, False)
    return templates.TemplateResponse("characters_list/characters_creation.html", {
        "request": request,
        "character_names": character_names,
        "project": project,
        "sub_page": "creation",
        **visual_settings
    })

@router.post("/create")
async def create_character(request: Request, project_name: str, name: str = Form(), prompt: str = Form()):
    project, project_path = get_project_by_name(project_name)
    character_names = get_project_story_objects_names(project_path, False)
    
    if(name in character_names):
        return {"message": "Character with this name already exists"}
    
    characters_file = os.path.join(project_path, "data/characters.json")
    
    data = get_safe_json(characters_file)
    id = get_highest_id(data)+1
    
    data[name] = {
        "id": id,
        "name": name,
        "user_name": name,
        "versions": {
            "default": {
                "description": "a character",
                "prompt": prompt,
                "image": ""
            }
        },
        "images": []
    }
    
    with open(characters_file, 'w') as file:
        json.dump(data, file, indent=4)
        
    project.characters_n = len(data)
    update_project_data(project, project_path)
    
    
@router.post("/copy")
async def character_copy(request: Request, project_name: str, name: str = Form()):
    project, project_path = get_project_by_name(project_name)
    character_names = get_project_story_objects_names(project_path, False)
    
    new_name = name + "_copy"
    count = 0
    while(new_name in character_names):
        count += 1
        new_name = name + "_copy_" + str(count)
    
    characters_file = os.path.join(project_path, "data/characters.json")
    
    data = get_safe_json(characters_file)
    
    id = get_highest_id(data)+1
    
    data[new_name] = data[name].copy()
    data[new_name]["name"] = new_name
    data[new_name]["user_name"] = get_free_user_name(new_name, data)
    data[new_name]["id"] = id
    
    with open(characters_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    project.characters_n = len(data)
    update_project_data(project, project_path)
    
    return {"message": new_name}

@router.post("/delete_character")
async def character_delete(request: Request, project_name: str, name: str = Form()):
    project, project_path = get_project_by_name(project_name)
    character_names = get_project_story_objects_names(project_path, False)
    
    if(not (name in character_names)):
        return {"message": "Invalid character name"}
    
    characters_file = os.path.join(project_path, "data/characters.json")
    
    data = get_safe_json(characters_file)
    
    
    for character in data.values():
        if(character["name"] == name):
            for image in character["images"]:
                if(check_if_image_exists(project_path, "characters", image["path"]) and not check_if_image_is_referenced(data, image["path"])):
                        os.remove(os.path.join(project_path, "images", "characters", image["path"]))
                        os.remove(os.path.join(project_path, "images", "sprites", image["path"]))
            break
    
    del data[name]
    
    with open(characters_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    project.characters_n = len(data)
    update_project_data(project, project_path)
    
    return {"message": "Character deleted"}


@router.get("/merge")
async def character_merge(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    visual_settings = get_visual_settings()
    
    characters = get_project_story_object_info(project_path, False)
    
    return templates.TemplateResponse("characters_list/characters_merge.html", {
        "request": request,
        "characters": characters,
        "project": project,
        "sub_page": "merge",
        **visual_settings
    })

@router.post("/merge")
async def character_merge(request: Request, project_name: str, first: str = Form(), second: str = Form()):
    if(first == second):
        return {"message": "Cannot merge the same character"}
    
    project, project_path = get_project_by_name(project_name)
    
    characters = get_project_story_object_info(project_path, False)
    if(first not in characters or second not in characters):
        return {"message": "Invalid characters"}
    
    characters_file = os.path.join(project_path, "data/characters.json")
    
    data = get_safe_json(characters_file)
    
    for version in data[second]["versions"]:
        new_name = version
        count = 0
        while(new_name in data[first]["versions"]):
            count += 1
            new_name = new_name + "_" + str(count)
        data[first]["versions"][new_name] = data[second]["versions"][version]
        
    for image in data[second]["images"]:
        if image not in data[first]["images"]:
            data[first]["images"].append(image)
    
    del data[second]
    
    with open(characters_file, 'w') as file:
        json.dump(data, file, indent=4)
        
    project.characters_n = len(data)
    update_project_data(project, project_path)
