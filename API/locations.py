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
async def read_location(request: Request, project_name: str):
    
    Url: str = "/project/"+project_name+"/locations/list"
    
    return RedirectResponse(url=Url, status_code=302)
    

@router.get("/list")
async def read_location_list(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    visual_settings = get_visual_settings()
    
    locations = get_project_story_objects(project_path, True)
    return templates.TemplateResponse("locations_list/locations_list.html", {
        "request": request,
        "locations": locations,
        "project": project,
        "sub_page": "list",
        **visual_settings
    })

@router.get("/creation")
async def location_creation(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    visual_settings = get_visual_settings()
    
    location_names = get_project_story_objects_names(project_path, True)
    return templates.TemplateResponse("locations_list/locations_creation.html", {
        "request": request,
        "location_names": location_names,
        "project": project,
        "sub_page": "creation",
        **visual_settings
    })

@router.post("/create")
async def create_location(request: Request, project_name: str, name: str = Form(), prompt: str = Form()):
    project, project_path = get_project_by_name(project_name)
    location_names = get_project_story_objects_names(project_path, True)
    
    if(name in location_names):
        return {"message": "location with this name already exists"}
    
    locations_file = os.path.join(project_path, "data/locations.json")
    
    data = get_safe_json(locations_file)
    
    data[name] = {
        "name": name,
        "user_name": name,
        "versions": {
            "default": {
                "description": "a location",
                "prompt": prompt,
                "image": ""
            }
        },
        "images": []
    }
    
    with open(locations_file, 'w') as file:
        json.dump(data, file, indent=4)
        
    project.locations_n = len(data)
    update_project_data(project, project_path)
    
    
@router.post("/copy")
async def location_copy(request: Request, project_name: str, name: str = Form()):
    project, project_path = get_project_by_name(project_name)
    location_names = get_project_story_objects_names(project_path, True)
    
    new_name = name + "_copy"
    count = 0
    while(new_name in location_names):
        count += 1
        new_name = name + "_copy_" + str(count)
    
    locations_file = os.path.join(project_path, "data/locations.json")
    
    data = get_safe_json(locations_file)
    
    data[new_name] = data[name].copy()
    data[new_name]["name"] = new_name
    data[new_name]["user_name"] = get_free_user_name(new_name, data)
    data[new_name]["id"] =  get_highest_id(data)+1
    
    with open(locations_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    project.locations_n = len(data)
    update_project_data(project, project_path)
    
    return {"message": new_name}

@router.post("/delete_location")
async def location_delete(request: Request, project_name: str, name: str = Form()):
    project, project_path = get_project_by_name(project_name)
    location_names = get_project_story_objects_names(project_path, True)
    
    if(not (name in location_names)):
        return {"message": "Invalid location name"}
    
    locations_file = os.path.join(project_path, "data/locations.json")
    
    data = get_safe_json(locations_file)
    
    
    for location in data.values():
        if(location["name"] == name):
            for image in location["images"]:
                if(check_if_image_exists(project_path, "locations", image["path"]) and not check_if_image_is_referenced(data, image["path"])):
                    os.remove(os.path.join(project_path, "images", "locations", image["path"]))
            break
    
    del data[name]
    
    with open(locations_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    project.locations_n = len(data)
    update_project_data(project, project_path)
    
    return {"message": "location deleted"}


@router.get("/merge")
async def location_merge(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    visual_settings = get_visual_settings()
    
    locations = get_project_story_object_info(project_path, True)
    
    return templates.TemplateResponse("locations_list/locations_merge.html", {
        "request": request,
        "locations": locations,
        "project": project,
        "sub_page": "merge",
        **visual_settings
    })

@router.post("/merge")
async def location_merge(request: Request, project_name: str, first: str = Form(), second: str = Form()):
    if(first == second):
        return {"message": "Cannot merge the same location"}
    
    project, project_path = get_project_by_name(project_name)
    
    locations = get_project_story_object_info(project_path, True)
    if(first not in locations or second not in locations):
        return {"message": "Invalid locations"}
    
    locations_file = os.path.join(project_path, "data/locations.json")
    
    data = get_safe_json(locations_file)
    
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
    
    with open(locations_file, 'w') as file:
        json.dump(data, file, indent=4)   
    
    project.locations_n = len(data)
    update_project_data(project, project_path)
