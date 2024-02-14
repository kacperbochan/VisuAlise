import json
import os
import datetime
from fastapi import APIRouter, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from models.models import Project, ProjectMenuData
from settings import global_settings as settings, load_user_settings
from typing import List
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory="templates/project")
projects_file = "projects.json"

def load_projects() -> List[ProjectMenuData]:
    if os.path.isfile(projects_file):
        try:
            with open(projects_file, 'r') as file:
                data = json.load(file)
                if data:
                    return [ProjectMenuData(**project) for project in data]
        except json.JSONDecodeError:
            pass
    return []


def get_project_by_name(project_name: str) -> Project:
    for project in load_projects():
        if project.name == project_name:
            project_path = os.path.join(project.path, "data", "project_data.json")
            if os.path.isfile(project_path):
                with open(project_path, 'r') as file:
                    data = json.load(file)
                    return Project(**data), project.path
            break
    return None


def get_model_lists():
    language_models = os.listdir(settings.llm_dir)
    diffusion_models = [file for file in os.listdir(settings.diffusion_dir) if file.endswith((".safetensors", ".ckpt"))]
    return {"language_models": language_models, "diffusion_models": diffusion_models}


def get_project_story_objects(project: Project, project_path:str,  location: bool = False):
    type = "locations" if location else "characters"
    story_object_file = os.path.join(project_path, "data", type+".json")
    if not os.path.isfile(story_object_file):
        with open(story_object_file, 'w') as file:
            file.write('{}')
            return []
    else:
        with open(story_object_file, 'r') as file:
            try:
                data = json.load(file)
                story_object_list = []
                for story_object in data.values():
                    image_path = os.path.join(project_path, "images", type, story_object["image"])
                    if not os.path.isfile(image_path):
                        image_path = None
                    else:
                        image_path = "\\" + image_path
                    story_object_list.append({"user_name": story_object["user_name"], "name": story_object["name"], "img": image_path})
                return story_object_list
            except json.JSONDecodeError:
                file_path_error = os.path.splitext(story_object_file)[0] + "_error.json"
                file.close()
                os.rename(story_object_file, file_path_error)
                with open(story_object_file, 'w') as new_file:
                    new_file.write('{}')
                return []


@router.get("/{project_name}")
async def read_project(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found or data file missing")
    
    return templates.TemplateResponse("base.html", {
        "request": request,
        "project": project
    })

@router.get("/{project_name}/characters")
async def read_character(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    
    characters_images = get_project_story_objects(project, project_path, False)
    
    return templates.TemplateResponse("character_list.html", {
        "request": request,
        "characters": characters_images,
        "project": project
    })

@router.get("/{project_name}/locations")
async def read_locations(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    
    location_images = get_project_story_objects(project, project_path, True)
    
    return templates.TemplateResponse("location_list.html", {
        "request": request,
        "locations": location_images,
        "project": project
    })

def get_story_object_data(project: Project, project_path: str, story_object_name:str, location: bool = False):
    type = "locations" if location else "characters"
    story_object_file = os.path.join(project_path, "data", type+".json")
    if not os.path.isfile(story_object_file):
        with open(story_object_file, 'w') as file:
            file.write('{}')
            return []
    else:
        with open(story_object_file, 'r') as file:
            try:
                data = json.load(file)
                
                for story_object in data.values():
                    if(story_object["name"] == story_object_name):
                        if(story_object["image"]!=None):
                            story_object["image"] = "\\"+os.path.join(project_path, "images", type, story_object["image"])
                        return(story_object)
                raise HTTPException(status_code=404, detail=(("location" if location else "character") + " not found"))
            except json.JSONDecodeError:
                file_path_error = os.path.splitext(story_object_file)[0] + "_error.json"
                file.close()
                os.rename(story_object_file, file_path_error)
                with open(story_object_file, 'w') as new_file:
                    new_file.write('{}')
                return []

@router.get("/images/")
async def get_images():
    image_directory = Path('static/images')
    image_files = [f"/static/images/{image.name}" for image in image_directory.glob("*.png")]
    return image_files

@router.get("/{project_name}/characters/{character_id}")
async def read_character(request: Request, project_name: str, character_id: str):
    
    project, project_path = get_project_by_name(project_name)
    character = get_story_object_data(project, project_path, character_id, False)
    
    return templates.TemplateResponse("character.html", {
        "request": request,
        "project": project,
        **character
    })

@router.get("/{project_name}/locations/{location_id}")
async def read_location(request: Request, project_name: str, location_id: str):
    
    project, project_path = get_project_by_name(project_name)
    location = get_story_object_data(project, project_path, location_id, True)
    
    return templates.TemplateResponse("location.html", {
        "request": request,
        "project": project,        
        **location
    })


@router.get("/{project_name}/model-lists")
async def get_model_lists_endpoint(project_name: str):
    return get_model_lists()

@router.get("/{project_name}/settings")
async def read_settings(request: Request, project_name: str):
    model_lists = get_model_lists()
    
    project, project_path = get_project_by_name(project_name)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "project": project,
        **model_lists,
    })
    
@router.post("/{project_name}/settings")
async def update_settings(request: Request, project_name: str, language_model: str = Form(...), diffusion_model: str = Form(...)):
    
    project, project_path = get_project_by_name(project_name)
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "language_models": os.listdir(settings.llm_dir),
        "diffusion_models": os.listdir(settings.diffusion_dir),
        "project": project
    })