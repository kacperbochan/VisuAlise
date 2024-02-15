import json
import os
import datetime
from fastapi import APIRouter, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from models.models import Project, ProjectMenuData, LLM, DiffusionModel
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

def get_visual_settings():
    return {
        "theme": settings.theme
    }

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
    
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("base.html", {
        "request": request,
        "project": project,
        **visual_settings
    })

@router.get("/{project_name}/characters")
async def read_character(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    
    characters_images = get_project_story_objects(project, project_path, False)
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("character_list.html", {
        "request": request,
        "characters": characters_images,
        "project": project,
        **visual_settings
    })

@router.get("/{project_name}/locations")
async def read_locations(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    
    location_images = get_project_story_objects(project, project_path, True)
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("location_list.html", {
        "request": request,
        "locations": location_images,
        "project": project,
        **visual_settings
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
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("character.html", {
        "request": request,
        "project": project,
        **character,
        **visual_settings
    })

@router.get("/{project_name}/locations/{location_id}")
async def read_location(request: Request, project_name: str, location_id: str):
    
    project, project_path = get_project_by_name(project_name)
    location = get_story_object_data(project, project_path, location_id, True)
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("location.html", {
        "request": request,
        "project": project,        
        **location,
        **visual_settings
    })


@router.get("/{project_name}/model-lists")
async def get_model_lists_endpoint(project_name: str):
    return get_model_lists()

@router.get("/{project_name}/settings")
async def read_settings(request: Request, project_name: str):
    model_lists = get_model_lists()
    visual_settings = get_visual_settings()
    project, project_path = get_project_by_name(project_name)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "project": project,
        **model_lists,
        **visual_settings
    })

@router.post("/{project_name}/settings/update/llm")
async def update_settings(request: Request, project_name: str, 
                        language_model: str = Form(...), 
                        llm_temperature: float = Form(...), 
                        llm_top_k: int = Form(...),
                        llm_top_p: float = Form(...),
                        llm_repetition_penalty: float = Form(...),
                        llm_max_length: int = Form(...)
                        ):
    
    project, project_path = get_project_by_name(project_name)
    
    model_lists = get_model_lists()
    
    if language_model not in model_lists["language_models"]:
        return {"message": "Invalid language model"}
    if llm_temperature < 0 or llm_temperature > 1:
        return {"message": "Invalid temperature"}
    if llm_top_k < 0:
        return {"message": "Invalid top_k"}
    if llm_top_p < 0 or llm_top_p > 1:
        return {"message": "Invalid top_p"}
    if llm_repetition_penalty < 0:
        return {"message": "Invalid repetition_penalty"}
    if llm_max_length < 2:
        return {"message": "Invalid max_length"}
    
    updated_model = LLM(
        model=language_model,
        temperature=llm_temperature,
        top_k=llm_top_k,
        top_p=llm_top_p,
        repetition_penalty=llm_repetition_penalty,
        max_length=llm_max_length
    )
    
    project.llm = updated_model
    
    project_json_file = project_path + "/data/project_data.json"
    
    with open(project_json_file, 'w') as file:
        json.dump(project.dict(), file, indent=4)
    
    return {"message": "LLM settings updated"}


@router.post("/{project_name}/settings/update/diffusion")
async def update_settings(request: Request, project_name: str, 
                        diffusion_model: str = Form(...), 
                        diffusion_steps: int = Form(...), 
                        diffusion_temperature: float = Form(...),
                        diffusion_batch: int = Form(...),
                        ):
    
    project, project_path = get_project_by_name(project_name)
    
    model_lists = get_model_lists()
    
    if diffusion_model not in model_lists["diffusion_models"]:
        return {"message": "Invalid diffusion model"}
    if diffusion_steps < 1:
        return {"message": "Invalid step amount"}
    if diffusion_temperature < 0 or diffusion_temperature > 30:
        return {"message": "Invalid temperature"}
    if diffusion_batch < 1:
        return {"message": "Invalid batch size"}
    
    updated_model = DiffusionModel(
        model=diffusion_model,
        steps=diffusion_steps,
        temperature=diffusion_temperature,
        batch=diffusion_batch
    )
    
    project.diffusion_model = updated_model
    
    project_json_file = project_path + "/data/project_data.json"
    
    with open(project_json_file, 'w') as file:
        json.dump(project.model_dump(), file, indent=4)
    
    return {"message": "Diffusion Model settings updated"}
