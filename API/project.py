import json
import os
import datetime
from fastapi import APIRouter, FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from models.models import Project, ProjectMenuData, LLM, DiffusionModel
from models.dto_models import StoryElementMiniDTO
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

def get_safe_json(file_path: str):
    response = {}
    if not os.path.isfile(file_path):
        with open(file_path, 'w') as file:
            file.write('{}')
            return {}
    else:
        with open(file_path, 'r') as file:
            try:
                response = json.load(file)
            except json.JSONDecodeError:
                file_path_error = os.path.splitext(file_path)[0] + "_error.json"
                file.close()
                os.rename(file_path, file_path_error)
                with open(file_path, 'w') as new_file:
                    new_file.write('{}')
                return {}
        return response

def get_project_prompts(project_path:str):
    story_object_file = os.path.join(project_path, "data", "characters.json")
    
    data = get_safe_json(story_object_file)

    transformed_data = {}
    for character, details in data.items():
        versions = details.get('versions', {})
        transformed_data[character] = {}
        for version, version_details in versions.items():
            prompt = version_details.get('prompt', '')
            transformed_data[character][version] = prompt

    # Convert the transformed data to JSON format
    return transformed_data



def get_project_story_objects(project_path:str,  location: bool = False):
    type = "locations" if location else "characters"
    story_object_file = os.path.join(project_path, "data", type+".json")
    
    data = get_safe_json(story_object_file)
                
    story_object_list = []
    
    for story_object in data.values():
        
        story_element_dto = StoryElementMiniDTO(
            name=story_object["name"], 
            user_name=story_object["user_name"], 
            description=story_object["versions"]["default"]["description"], 
            image=story_object["versions"]["default"]["image"], 
            prompt=story_object["versions"]["default"]["prompt"])
        
        story_element_dto.image_path = os.path.join(project_path, "images", type, story_element_dto.image)
        
        if not os.path.isfile(story_element_dto.image_path):
            story_element_dto.image_path = None
        else:
            story_element_dto.image_path = "\\" + story_element_dto.image_path
        story_object_list.append(story_element_dto)
    return story_object_list

def add_image_to_story_object(project_name:str, story_object_name:str, image_name: str, prompt: str, location: bool = False):
    
    project, project_path = get_project_by_name(project_name)
    
    type = "locations" if location else "characters"
    story_object_file = os.path.join(project_path, "data", type+".json")
    
    data = get_safe_json(story_object_file)
    
    if "images" not in data.get(story_object_name, {}):
        if story_object_name not in data:
            data[story_object_name] = {}
        data[story_object_name]["images"] = []
    
    new_image = {
        "path": image_name+".png",
        "prompt": prompt
    }
    x = data[story_object_name]["images"]
    data[story_object_name]["images"].append(new_image)
    
    with open(story_object_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    return {"message": "Image added to story object"}

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
    visual_settings = get_visual_settings()
    
    characters = get_project_story_objects(project_path, False)
    return templates.TemplateResponse("character_list.html", {
        "request": request,
        "characters": characters,
        "project": project,
        **visual_settings
    })

@router.get("/{project_name}/locations")
async def read_locations(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    
    locations = get_project_story_objects(project_path, True)
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("location_list.html", {
        "request": request,
        "locations": locations,
        "project": project,
        **visual_settings
    })

style_prompts = {
    "characters":{
        "default":  """(Full body character shot), soft lines, animation styled, portrait, solid color white background, Vibrant animation style, cartoon style, solo, centered image, animated character, looking at camera, standing in a relaxed pose""",
        "anime": """(Full body character shot), (anime coloring, anime screencap, anime style), portrait, solid color white background, Vibrant anime style, anime style, solo, centered image, animated character, looking at camera, standing in a relaxed pose""",
    },
    "locations":{
        "default": """(Landscape), soft lines, animation styled, portrait, solid color white background, Vibrant animation style, cartoon style, solo, centered image, animated character, looking at camera, standing in a relaxed pose""",
        "anime": """(Landscape), (anime coloring, anime screencap, anime style), portrait, solid color white background, Vibrant anime style, anime style, solo, centered image, animated character, looking at camera, standing in a relaxed pose"""
    }
    
}

@router.get("/{project_name}/generation")
async def generation_page(request: Request, project_name: str):
    
    project, project_path = get_project_by_name(project_name)
    
    characters = get_project_story_objects(project_path, False)
    locations = get_project_story_objects(project_path, True)
    model_lists = get_model_lists()
    
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("generation/generation_base.html", {
        "request": request,
        "project": project,
        "sub_page": "txt2img",
        "characters": characters,
        "locations": locations,
        "style_prompts": style_prompts,
        **model_lists,
        **visual_settings
    })

@router.get("/{project_name}/promptblock")
async def get_promptblock(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    return get_project_prompts(project_path)



@router.get("/{project_name}/generate/get_prompt/{type}/{name}")
async def get_prompt(request: Request, project_name: str, type:str, name: str):
    project, project_path = get_project_by_name(project_name)
    if type == "character":
        characters = get_project_story_objects(project_path, False)
        for character in characters:
            if character.name == name:
                return character.prompt
    elif type == "location":
        locations = get_project_story_objects(project_path, True)
        for location in locations:
            if location["name"] == name:
                return location["prompt"]

@router.get("/{project_name}/generation/{sub_page}")
async def generation_sub_page(request: Request, project_name: str, sub_page: str):
    
    project, project_path = get_project_by_name(project_name)
    visual_settings = get_visual_settings()
    
    characters = get_project_story_objects(project_path, False)
    locations = get_project_story_objects(project_path, True)
    
    return templates.TemplateResponse("generation/generation_base.html", {
        "request": request,
        "project": project,
        "sub_page": {sub_page},
        "characters": characters,
        "locations": locations,
        **visual_settings
    })

@router.get("/{project_name}/generation/txt2img/template", response_class=HTMLResponse)
async def txt2img_page(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    
    characters = get_project_story_objects(project_path, False)
    locations = get_project_story_objects(project_path, True)
    
    model_lists = get_model_lists()
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("generation/generation_txt2img.html", {
        "request": request,
        "project": project,
        "characters": characters,
        "locations": locations,
        **model_lists,
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
                        images = []
                        for image in story_object["images"]:
                            if(os.path.isfile(os.path.join(project_path, "images", type, image["path"]))):
                                images.append(image)
                        story_object["images"] = images
                        return(story_object)
                raise HTTPException(status_code=404, detail=(("location" if location else "character") + " not found"))
            except json.JSONDecodeError:
                file_path_error = os.path.splitext(story_object_file)[0] + "_error.json"
                file.close()
                os.rename(story_object_file, file_path_error)
                with open(story_object_file, 'w') as new_file:
                    new_file.write('{}')
                return []

@router.get("/{project_name}/characters/{character_id}/")
async def read_character(request: Request, project_name: str, character_id: str):
    
    Url: str = "/project/"+project_name+"/characters/"+character_id+"/info"
    
    return RedirectResponse(url=Url, status_code=302)
    



@router.get("/{project_name}/characters/{character_id}/info", response_class=HTMLResponse)
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

@router.get("/{project_name}/characters/{character_id}/gallery", response_class=HTMLResponse)
async def read_character(request: Request, project_name: str, character_id: str):
    
    project, project_path = get_project_by_name(project_name)
    character = get_story_object_data(project, project_path, character_id, False)
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("character/character_gallery.html", {
        "request": request,
        "project": project,
        "sub_page": "gallery",
        **character,
        **visual_settings
    })

@router.get("/{project_name}/characters/{character_id}/text_data", response_class=HTMLResponse)
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

@router.get("/{project_name}/characters/{character_id}/versions", response_class=HTMLResponse)
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

def get_checked_version(project_name:str, story_object_name:str, version_name: str, location: bool = False):
    project, project_path = get_project_by_name(project_name)
    
    type = "locations" if location else "characters"
    story_object_file = os.path.join(project_path, "data", type+".json")
    
    data = get_safe_json(story_object_file)
    
    if story_object_name not in data:
        return {"message": "No such story object"}
    if version_name not in data[story_object_name]['versions']:
        return {"message": "No such version"}
    
    return None, data, story_object_file

@router.post("/{project_name}/{type}/{story_object_name}/versions/update_name_and_prompt")
async def update_story_object_version(request: Request, project_name:str, type: str, story_object_name:str, version_name: str = Form(), new_version_name: str = Form(), new_version_prompt: str = Form()):
    
    if(type != "characters" and type != "locations"):
        return {"message": "Invalid type"}
    if(version_name == 'default' and version_name != new_version_name):
        return {"message": "Cannot change the default version name"}
    
    message, data, story_object_file = get_checked_version(project_name, story_object_name, version_name, type=="locations")
    if(message != None):
        return message
    
    if(version_name != new_version_name):    
        data[story_object_name]['versions'][new_version_name] = data[story_object_name]['versions'][version_name]
        del data[story_object_name]['versions'][version_name]
    data[story_object_name]['versions'][new_version_name]['prompt'] = new_version_prompt
    
    with open(story_object_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    return {"message": "Version updated"}

@router.post("/{project_name}/{type}/{story_object_name}/versions/copy_version")
async def clone_story_object_version(project_name:str, type: str, story_object_name:str, version_name: str = Form()):
    if(type != "characters" and type != "locations"):
        return {"message": "Invalid type"}    
    
    message, data, story_object_file = get_checked_version(project_name, story_object_name, version_name, type=="locations")
    if(message != None):
        return message
    
    new_version_name = version_name + "_copy"
    counter = 0
    while(new_version_name in data[story_object_name]['versions']):
        counter += 1
        new_version_name = version_name + "_copy_" + str(counter)
    
    data[story_object_name]['versions'][new_version_name] = data[story_object_name]['versions'][version_name]
    
    with open(story_object_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    return {"message": "Version cloned"}

@router.post("/{project_name}/{type}/{story_object_name}/versions/delete_version")
async def delete_story_object_version(project_name:str, type: str, story_object_name:str, version_name: str = Form()):
    
    if(type != "characters" and type != "locations"):
        return {"message": "Invalid type"}
    if(version_name == 'default'):
        return {'message' : 'Cannot delete the default version'}
    
    message, data, story_object_file = get_checked_version(project_name, story_object_name, version_name, type=="locations")
    if(message != None):
        return message

    del data[story_object_name]['versions'][version_name]
    
    with open(story_object_file, 'w') as file:
        json.dump(data, file, indent=4)
    
    return {"message": "Version deleted"}
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
                        diffusion_cfg: float = Form(...),
                        diffusion_batch: int = Form(...),
                        ):
    
    project, project_path = get_project_by_name(project_name)
    
    model_lists = get_model_lists()
    
    if diffusion_model not in model_lists["diffusion_models"]:
        return {"message": "Invalid diffusion model"}
    if diffusion_steps < 1:
        return {"message": "Invalid step amount"}
    if diffusion_cfg < 0 or diffusion_cfg > 30:
        return {"message": "Invalid temperature"}
    if diffusion_batch < 1:
        return {"message": "Invalid batch size"}
    
    updated_model = DiffusionModel(
        model=diffusion_model,
        steps=diffusion_steps,
        cfg=diffusion_cfg,
        batch=diffusion_batch
    )
    
    project.diffusion_model = updated_model
    
    project_json_file = project_path + "/data/project_data.json"
    
    with open(project_json_file, 'w') as file:
        json.dump(project.model_dump(), file, indent=4)
    
    return {"message": "Diffusion Model settings updated"}
