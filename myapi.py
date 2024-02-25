import asyncio
import aiohttp
import json
from math import floor
import os
import datetime
import random
import threading
import subprocess
import time
from urllib import request
from fastapi import FastAPI, HTTPException, Request, Form, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from models.models import Project
from settings import global_settings as settings, load_user_settings
from typing import List
from pathlib import Path
from API.menu import router as menu_router
from API.project import router as projects_router
from API.characters import router as characters_router
from API.locations import router as locations_router
from API.character import router as character_router
from API.location import router as location_router
from API.project import add_image_to_story_object
import requests

if(not os.path.exists(settings.projects_dir)):
    os.makedirs(settings.projects_dir)

load_user_settings()
app = FastAPI()
app.include_router(menu_router, prefix="/menu")
app.include_router(projects_router, prefix="/project")
app.include_router(characters_router, prefix="/project/{project_name}/characters")
app.include_router(locations_router, prefix="/project/{project_name}/locations")
app.include_router(character_router, prefix="/project/{project_name}/character/{character_id}")
app.include_router(location_router, prefix="/project/{project_name}/location/{location_id}")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/projects", StaticFiles(directory="projects"), name="projects")

Model_Status = {
    "LLM": "Not Loaded",
    "Diffusion": "Not Loaded"
}

Model_Thread: threading.Thread

def check_server_is_up(url, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("ComfyUI server is up and running.")
                return True
        except requests.ConnectionError:
            # Server not up yet
            pass
        time.sleep(5)  # Wait for 5 seconds before trying again
    print("Timed out waiting for ComfyUI server to start.")
    return False

@app.exception_handler(HTTPException)
async def handle_404_exception(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        if exc.detail == "Project not found":
            return RedirectResponse(url="/menu", status_code=302)
        if exc.detail == "character not found":
            project_name = request.path_params["project_name"]
            new_url = f"/project/{project_name}/characters/"
            return RedirectResponse(url=new_url, status_code=302)
        if exc.detail == "location not found":
            project_name = request.path_params["project_name"]
            new_url = f"/project/{project_name}/locations/"
            return RedirectResponse(url=new_url, status_code=302)
        return RedirectResponse(url="/menu", status_code=302)
    return exc

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/menu", status_code=302)

def start_comfy_ui():
    subprocess.run(["python", "repositories/ComfyUI-master/main.py"])    


@app.get("/models/status")
async def get_model_status():
    return Model_Status

@app.post("/models/unload")
async def unload_model():
    if Model_Thread.is_alive():
        Model_Thread.terminate()

@app.post("/models/Diffusion/load")
async def load_diffusion_model():
    Model_Thread = threading.Thread(target=start_comfy_ui)
    Model_Thread.start()            
    check_server_is_up("http://127.0.0.1:8188") # Wait for the server to start
    Model_Status["Diffusion"] = "loaded"

@app.post("/models/LLM/load")
async def load_llm_model():
    pass

def get_latest_images(directory: str):
        # Get a list of all .png files in the directory with their full paths
    list_of_files = [os.path.join(directory, file) for file in os.listdir(directory) 
                    if os.path.isfile(os.path.join(directory, file)) and file.endswith('.png')]
    # Find the file with the latest creation time
    latest_file = max(list_of_files, key=os.path.getctime, default=None)
    # Return only the file name, or None if no .png files are found
    return os.path.basename(latest_file) if latest_file else None

def queue_prompt(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    req =  request.Request("http://127.0.0.1:8188/prompt", data=data)
    request.urlopen(req)    


def update_workflow_by_title(prompt_workflow, title:str,  **kwargs):
    for x in prompt_workflow.values():
        if x["_meta"]["title"]==title:
            for key, value in kwargs.items():
                x["inputs"][key] = value

@app.get("/get_latest_location_image")
async def get_generated_images(project: str):
    location_images_dir = f"projects\\{project}\\images\\locations"
    image =  get_latest_images(location_images_dir)
    return {"image_directory": location_images_dir,"image": image }

@app.get("/get_latest_character_image")
async def get_generated_images(project: str):
    character_images_dir = f"projects\\{project}\\images"
    image =  get_latest_images(character_images_dir+"\\characters")
    return {"image_directory": character_images_dir, "image": image}


negative_prompt_base = """"""

def get_file_number(directory:str, filename:str, skip:int = 0):
    
    file = f"{filename}_{skip:05}" if (skip>0) else filename
    file_path = os.path.join(directory, file)+".png"
    
    while os.path.isfile(file_path):
        skip = skip + 1
        file = f"{filename}_{skip:05}"
        file_path = os.path.join(directory, file)+".png"
    
    return file, skip

def getFileNames(directory:str, filename:str, amount:int = 1) -> List[str]:
    response = []
    skip = 0
    for i in range(amount):
        file, skip = get_file_number(directory, filename, skip)
        response.append(file)
        skip = skip + 1
    
    return response    

@app.post("/generate_image")
async def generate_image(
                        project_name: str = Form(),
                        prompt: str = Form(), 
                        style_prompt: str = Form(),
                        negative_prompt: str = Form(""), 
                        image_type: str = Form(), 
                        model: str = Form(), 
                        seed: float = Form(),
                        steps: int = Form(),
                        batch_amount: int = Form(),
                        cfg: int = Form(),
                        name: str = Form(),
                        version: str = Form()
                        ):
    seed = floor(seed)
    if(seed<-1): seed = -1
    if(steps<1): steps = 1
    if(batch_amount<1): batch_amount = 1
    if(cfg<1): cfg = 1
    
    if Model_Status["LLM"] == "loaded": return {"response": "LLM loaded"}
    if Model_Status["Diffusion"] != "loaded": await load_diffusion_model()
    
    images_directory = os.path.join(os.getcwd(), f'projects\\{project_name}\\images')
    
    if(image_type == "character"):
        with open('AI/Diffusion/generate_character.json', 'r') as f:
            data = json.load(f)
        
        ch_directory = os.path.join(images_directory, "characters")
        sp_directory = os.path.join(images_directory, "sprites")
        
        filenames = getFileNames(ch_directory, name+"_"+version,batch_amount)
        update_workflow_by_title(data,"Save_Default", directory=ch_directory, filename=filenames[0])
        update_workflow_by_title(data,"Save_Sprite", directory=sp_directory, filename=filenames[0])
        
        update_workflow_by_title(data,"Empty_Latent_Image", width=512, height=768)
        
    elif(image_type == "location"):
        with open('AI/Diffusion/generate_location.json', 'r') as f:
            data = json.load(f)
        
        loc_directory = os.path.join(images_directory, "locations")
        
        filenames = getFileNames(loc_directory, name+"_"+version,batch_amount)
        
        update_workflow_by_title(data,"Save_Default", directory=loc_directory, filename=filenames[0])
        update_workflow_by_title(data,"Empty_Latent_Image", width=1792, height=1024)
    else:
        return {"response": "Invalid image type"}
    
    full_prompt = style_prompt+" , "+prompt
    
    update_workflow_by_title(data,"Load_Checkpoint",ckpt_name = model)
    update_workflow_by_title(data,"Prompt",text = full_prompt)
    update_workflow_by_title(data,"Negative_Prompt",text = negative_prompt_base+negative_prompt)
    update_workflow_by_title(data,"KSampler",seed = random.randint(0, 1000000000000000) if seed == -1 else seed, steps = steps, cfg = cfg)
    
    if(seed==-1):
        for batch in range(batch_amount):
            seed = random.randint(0, 1000000000000000)
            update_workflow_by_title(data,"KSampler",seed = seed)
            
            update_workflow_by_title(data,"Save_Default", filename=filenames[batch])
            update_workflow_by_title(data,"Save_Sprite", filename=filenames[batch])
            queue_prompt(data)
            
            add_image_to_story_object(project_name, name, filenames[batch], full_prompt, image_type=="location")
        
    else :
        for batch in range(batch_amount):
            queue_prompt(data)
            seed = seed + 1
            update_workflow_by_title(data,"KSampler",seed = seed)
            update_workflow_by_title(data,"Save_Default", filename=filenames[batch])
            add_image_to_story_object(project_name, name, filenames[batch], full_prompt, image_type=="location")
