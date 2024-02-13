import json
import os
import datetime
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from models.models import Project
from settings import global_settings as settings
from typing import List
from pathlib import Path
import re

if(not os.path.exists(settings.projects_dir)):
    os.makedirs(settings.projects_dir)

settings.check_settings_file()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/projects", StaticFiles(directory="projects"), name="projects")
templates = Jinja2Templates(directory="templates")


class FolderPath(BaseModel):
    folderPath: str

def load_projects() -> List[Project]:
    if os.path.isfile(settings.projects_json_path):
        try:
            with open(settings.projects_json_path, 'r') as file:
                data = json.load(file)
                if data:
                    return [Project(**project) for project in data]
        except json.JSONDecodeError:
            pass
    return []

def save_projects(projects_db: List[Project]):
    with open(settings.projects_json_path, 'w') as file:
        json.dump([project.dict() for project in projects_db], file, indent=4)

projects_db = load_projects()


def get_project_by_name(project_name: str) -> Project:
    for project in projects_db:
        if project.name == project_name:
            return project
    raise HTTPException(status_code=404, detail="Project not found")


def get_model_lists():
    language_models = os.listdir(settings.llm_dir)
    diffusion_models = [file for file in os.listdir(settings.diffusion_dir) if file.endswith((".safetensors", ".ckpt"))]
    return {"language_models": language_models, "diffusion_models": diffusion_models}

def get_project_data(project: Project):
    project_title = "Project " + str(project.name)
    
    characters_file = os.path.join(project.path, "characters", "characters.json")
    locations_file = os.path.join(project.path, "locations", "locations.json")

    def count_objects_in_json(file_path: str) -> int:
        if not os.path.isfile(file_path):
            with open(file_path, 'w') as file:
                file.write('{}')
                return 0
        else:
            with open(file_path, 'r') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    file_path_error = os.path.splitext(file_path)[0] + "_error.json"
                    file.close()
                    os.rename(file_path, file_path_error)
                    with open(file_path, 'w') as new_file:
                        new_file.write('{}')
                    return 0
            return len(data)

    characters_n = count_objects_in_json(characters_file)
    locations_n = count_objects_in_json(locations_file)
    return {
        "project_title": project_title,
        "project_name": project.name,
        "characters_n": characters_n,
        "locations_n": locations_n
        }

def get_project_story_objects(project: Project, location: bool = False):
    type = "locations" if location else "characters"
    story_object_file = os.path.join(project.path, type, type+".json")
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
                    image_path = os.path.join("projects", project.name, type, "images", story_object["image"])
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

def note_project_interaction(project: Project):
    project.last_opened = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_projects(projects_db)
    return project

@app.get("/", response_class=HTMLResponse)
async def list_projects(request: Request):
    sorted_projects = sorted(projects_db, key=lambda project: project.last_opened, reverse=True)
    return templates.TemplateResponse("projects_menu.html", {"request": request, "projects": sorted_projects})

@app.exception_handler(HTTPException)
async def handle_404_exception(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        if exc.detail == "Project not found":
            return RedirectResponse(url="/", status_code=302)
        if exc.detail == "character not found":
            project_name = request.path_params["project_name"]
            new_url = f"/project/{project_name}/characters/"
            return RedirectResponse(url=new_url, status_code=302)
        if exc.detail == "location not found":
            project_name = request.path_params["project_name"]
            new_url = f"/project/{project_name}/locations/"
            return RedirectResponse(url=new_url, status_code=302)
    return exc

@app.get("/open/{project_name}", response_class=HTMLResponse)
async def open_project(request: Request, project_name: str):
    project  = get_project_by_name(project_name)
    if note_project_interaction(project_name) is not None:    
        note_project_interaction(project)
        return templates.TemplateResponse("open_project.html", {"request": request, "project": project})
        
    raise HTTPException(status_code=404, detail="Project not found")

@app.get("/project/add", response_class=HTMLResponse)
async def add_project_form(request: Request):
    return templates.TemplateResponse("add_project.html", {"request": request})

@app.get("/project/add/existing", response_class=HTMLResponse)
async def add_project_form(request: Request):
    return templates.TemplateResponse("add_existing_project.html", {"request": request})

@app.post("/project/add")
async def add_project(title: str = Form(...)):
    project = Project(name=title, last_opened=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    project.last_opened = str(project.last_opened)  # Convert datetime to string
    
    def sanitize_project_name(name: str) -> str:
        name = name.lower()
        name = re.sub(r"[^\w\s-]", "", name)
        name = name.strip()
        name = name.replace(" ", "_")
        return name

    project_dir = os.path.join(settings.projects_dir, sanitize_project_name(project.name))

    # Check if the directory already exists
    if os.path.exists(project_dir):
        # Append a number to the directory name
        count = 1
        while os.path.exists(f"{project_dir}_{count}"):
            count += 1
        project_dir = f"{project_dir}_{count}"

    os.makedirs(project_dir)

    # Create "characters" folder
    characters_dir = os.path.join(project_dir, "characters")
    os.makedirs(characters_dir)
    characters_json_file = os.path.join(characters_dir, "characters.json")
    with open(characters_json_file, "w") as f:
        f.write("{}")

    # Create "locations" folder
    locations_dir = os.path.join(project_dir, "locations")
    os.makedirs(locations_dir)
    locations_json_file = os.path.join(locations_dir, "locations.json")
    with open(locations_json_file, "w") as f:
        f.write("{}")
    
    project.path = project_dir

    projects_db.append(project)
    save_projects(projects_db)
    
    return RedirectResponse(url='/', status_code=303)

@app.get("/project/{project_name}")
async def read_project(request: Request, project_name: str):
    
    project = get_project_by_name(project_name)
    
    project_data = get_project_data(project)
    
    return templates.TemplateResponse("base.html", {
        "request": request,
        **project_data
    })

@app.get("/project/{project_name}/characters")
async def read_character(request: Request, project_name: str):
    project = get_project_by_name(project_name)
    project_data = get_project_data(project)
    
    characters_images = get_project_story_objects(project)
    
    return templates.TemplateResponse("character_list.html", {
        "request": request,
        "characters": characters_images,
        **project_data
    })

@app.get("/project/{project_name}/locations")
async def read_locations(request: Request, project_name: str):
    project = get_project_by_name(project_name)
    project_data = get_project_data(project)
    
    location_images = get_project_story_objects(project, True)
    
    return templates.TemplateResponse("location_list.html", {
        "request": request,
        "locations": location_images,
        **project_data
    })

def get_story_object_data(project: Project, story_object_name:str, location: bool = False):
    type = "locations" if location else "characters"
    story_object_file = os.path.join(project.path, type, type+".json")
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
                            story_object["image"] = "\\"+os.path.join("projects", project.name, type, "images", story_object["image"])
                        return(story_object)
                raise HTTPException(status_code=404, detail=(("location" if location else "character") + " not found"))
            except json.JSONDecodeError:
                file_path_error = os.path.splitext(story_object_file)[0] + "_error.json"
                file.close()
                os.rename(story_object_file, file_path_error)
                with open(story_object_file, 'w') as new_file:
                    new_file.write('{}')
                return []

@app.get("/images/")
async def get_images():
    image_directory = Path('static/images')
    image_files = [f"/static/images/{image.name}" for image in image_directory.glob("*.png")]
    return image_files

@app.get("/project/{project_name}/characters/{character_id}")
async def read_character(request: Request, project_name: str, character_id: str):
    
    project = get_project_by_name(project_name)
    project_data= get_project_data(project)
    character = get_story_object_data(project, character_id, False)
    
    return templates.TemplateResponse("character.html", {
        "request": request,
        **character,
        **project_data        
    })

@app.get("/project/{project_name}/locations/{location_id}")
async def read_location(request: Request, project_name: str, location_id: str):
    
    project = get_project_by_name(project_name)
    project_data= get_project_data(project)
    location = get_story_object_data(project, location_id, True)
    
    return templates.TemplateResponse("location.html", {
        "request": request,
        **location,
        **project_data
    })


@app.get("/project/{project_name}/model-lists")
async def get_model_lists_endpoint(project_name: str):
    return get_model_lists()

@app.get("/project/{project_name}/settings")
async def read_settings(request: Request, project_name: str):
    model_lists = get_model_lists()
    
    project = get_project_by_name(project_name)
    project_data = get_project_data(project)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        **project_data,
        **model_lists,
    })
    
@app.post("/project/{project_name}/settings")
async def update_settings(request: Request, project_name: str, language_model: str = Form(...), diffusion_model: str = Form(...)):
    
    project_data = get_project_data(project_name)
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "language_models": os.listdir(settings.llm_dir),
        "diffusion_models": os.listdir(settings.diffusion_dir),
        **project_data,
    })