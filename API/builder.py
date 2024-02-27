import json
import os
import datetime
import random
import subprocess
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
from API.project import get_project_by_name, get_story_object_data, get_visual_settings, get_project_story_objects, get_text_data
import shutil
import re
import asyncio

router = APIRouter()
templates = Jinja2Templates(directory="templates/project")

def get_objects_without_images(project_path: str):
    characters= {}
    locations= {}
        
    characters_file = os.path.join(project_path, "data", "characters.json")
    locations_file = os.path.join(project_path, "data", "locations.json")
    
    with open(characters_file, 'r') as file:
        characters_data = json.load(file)
    with open(locations_file, 'r') as file:
        locations_data = json.load(file)
    
    characters = {key: value for key, value in characters_data.items() if "image" not in value}
    locations = {key: value for key, value in locations_data.items() if "image" not in value}
    
    return characters, locations

async def send_images(project_path: str, game_folder: str):
    output_folder = os.path.join(game_folder, "game", "images")
    
    output_images = []
    output_names = []
    
    sprites_dir = os.path.join(os.getcwd(), project_path, "images", "sprites")
    locations_dir = os.path.join(os.getcwd(), project_path, "images", "locations")
    
    characters_file = os.path.join(project_path, "data", "characters.json")
    locations_file = os.path.join(project_path, "data", "locations.json")
    
    with open(characters_file, 'r') as file:
        characters = json.load(file)
    with open(locations_file, 'r') as file:
        locations = json.load(file)
    
    for character in characters.values():
        for version, values in character["versions"].items():
            output_images.append(os.path.join(sprites_dir, values["image"]))
            output_names.append(character["name"]+"_"+version+".png")
    
    for location in locations.values():
        for version, values in location["versions"].items():
            output_images.append(os.path.join(locations_dir, values["image"]))
            output_names.append(location["name"]+"_"+version+".png")
    
    for index, image in enumerate(output_images):
        if image[-3:] == "png":
            shutil.copy(image, output_folder +"\\" +output_names[index].lower())
    


async def generate_game_script(project_path: str, game_folder: str):
    return True

async def launch_game(game_folder: str):
    run = os.path.join(game_folder, "Project.exe")
    subprocess.run([run])
    

async def replace_in_file(filename, new_value):
    with open(filename, 'r', encoding='utf-8') as file:
        file_contents = file.read()

    pattern = "Project-1708981541"
    match = re.search(pattern, file_contents)
    
    new_number = str(random.randint(10**(9), 10**9))
    file_contents = re.sub(pattern, f"{new_value}-{new_number}", file_contents)
    
    file_contents = file_contents.replace("Project", new_value)

    with open(filename, 'w', encoding='utf-8') as file:
        file.write(file_contents)

async def remove_folder(project_path: str):
    game_folder = os.path.join(os.getcwd(), project_path, "game")
    if(os.path.isdir(game_folder)):
        shutil.rmtree(game_folder)

async def rename_files(game_folder: str, project_name: str):
    exe_file = os.path.join(game_folder, "Project.exe")
    py_file = os.path.join(game_folder, "Project.py")
    sh_file = os.path.join(game_folder, "Project.sh")
    shutil.copy(exe_file, os.path.join(game_folder, f"{project_name}.exe"))
    shutil.copy(py_file, os.path.join(game_folder, f"{project_name}.py"))
    shutil.copy(sh_file, os.path.join(game_folder, f"{project_name}.sh"))

async def setup_game_folder(game_folder: str, project_name: str):
    renpy_project_files = os.path.join(os.getcwd(), "renpy", "project_files")
    shutil.copytree(renpy_project_files, game_folder)
    renpy_exe_file = os.path.join(os.getcwd(), "renpy", "exe", "Project.exe")
    shutil.copy(renpy_exe_file, game_folder)

async def generate_distribution(project_path: str, project_name: str):
    game_folder = await prepare_game_files(project_path, project_name, False)
    await send_images(project_path, game_folder)
    await generate_game_script(project_path, game_folder)
    
async def prepare_game_files(project_path: str, project_name: str, testing: bool = True):
    game_folder = os.path.join(os.getcwd(),project_path, "game")
    if(not testing):
        count = 0
        while(os.path.isdir(game_folder)):
            game_folder = os.path.join(os.getcwd(),project_path, f"game_{count}")
            count += 1
    if(os.path.isdir(game_folder)): return
    await setup_game_folder(game_folder, project_name)
    await rename_files(game_folder, project_name)
    await replace_in_file(os.path.join(game_folder, "game", "options.rpy"), project_name)
    if(not testing):
        return game_folder

def load_scenes(project_path: str):
    scenes_file = os.path.join(project_path, "data", "build_data.json")
    with open(scenes_file, 'r') as file:
        scenes = json.load(file)
    return scenes

@router.get("")
async def build_page(request: Request, project_name: str):
    
    project, project_path = get_project_by_name(project_name)
    characters, locations = get_objects_without_images(project_path)
    scenes = load_scenes(project_path)
    
    text=""
    file_path = get_text_data(project_path)
    if(file_path != ""):  
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    
    visual_settings = get_visual_settings()
    return templates.TemplateResponse("builder.html", {
        "request": request,
        "project": project,
        "characters": characters,
        "scenes": scenes,
        "locations": locations,
        "providedText": text,
        **visual_settings
    })


@router.post("/save")
async def save_game(project_name: str, body = Body(...)):
    data = body["scenes"]
    
    project, project_path = get_project_by_name(project_name)
    
    build_data = os.path.join(project_path, "data", "build_data.json")
    with open(build_data, 'w') as file:
        json.dump(data, file, indent=4)
    
    return {"status": "success"}

@router.post("/generate")
async def generate_game(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    await prepare_game_files(project_path, project_name)
    game_folder = os.path.join(os.getcwd(),project_path, "game")
    await send_images(project_path, game_folder)
    
    return {"status": "success"}

@router.post("/start")
async def start_game(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    if(not os.path.isdir(os.path.join(os.getcwd(), project_path, "game"))):
        await prepare_game_files(project_path, project_name)
        
    asyncio.create_task(await launch_game(os.path.join(os.getcwd(), project_path, "game")))

@router.post("/build")
async def build_distribution(request: Request, project_name: str):
    project, project_path = get_project_by_name(project_name)
    await generate_distribution(project_path, project_name)