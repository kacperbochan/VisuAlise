from fastapi import Request, Form, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
import datetime
import json
import os
import re

from settings import global_settings as settings
from models.models import Project, ProjectMenuData

router = APIRouter()
projects_file = "projects.json"
templates = Jinja2Templates(directory="templates/main_menu")

# -------------------------
# SECTION: Functions
# -------------------------

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


def add_project_data(project: ProjectMenuData):
    projects_db = load_projects()
    projects_db.insert(0, project)  # Add project at the beginning of the list

    with open(projects_file, 'w') as file:
        json.dump([project.model_dump() for project in projects_db], file, indent=4)


def create_project_path(user_name: str) -> bool:
    def sanitize_project_name(name: str) -> str:
        name = name.lower()
        name = re.sub(r"[^\w\s-]", "", name)
        name = name.strip()
        name = name.replace(" ", "_")
        return name

    project_dir = os.path.join(settings.projects_dir, sanitize_project_name(user_name))

    # Check if the directory already exists
    if os.path.exists(project_dir):
        # Append a number to the directory name
        count = 1
        while os.path.exists(f"{project_dir}_{count}"):
            count += 1
        project_dir = f"{project_dir}_{count}"

    return project_dir


def create_empty_json(file_path: str):
    with open(file_path, "w") as f:
        f.write("{}")

def create_file_structure(project_dir: str):
    #make project directory    
    os.makedirs(project_dir)
    # Create "images" folder
    os.makedirs(os.path.join(project_dir, "images"))
    
    # Create "sprites" folder for cut outs of characters
    os.makedirs(os.path.join(project_dir, "images", "sprites"))
    
    # Create "characters" folder
    os.makedirs(os.path.join(project_dir, "images", "characters"))
    
    # Create "backgrounds" folder
    os.makedirs(os.path.join(project_dir, "images", "backgrounds"))
    
    # Create "data" folder
    os.makedirs(os.path.join(project_dir, "data"))
    
    # Create "texts" folder
    os.makedirs(os.path.join(project_dir, "texts"))
    
    # Create "characters" and "locations" json files
    create_empty_json(os.path.join(project_dir, "data", "characters.json"))
    create_empty_json(os.path.join(project_dir, "data", "locations.json"))
    create_empty_json(os.path.join(project_dir, "data", "project_data.json"))
    create_empty_json(os.path.join(project_dir, "data", "text_data.json"))
    create_empty_json(os.path.join(project_dir, "data", "build_data.json"))


# -------------------------
# SECTION: Endpoints
# -------------------------


@router.get("/", response_class=HTMLResponse)
async def list_projects(request: Request):
    
    sorted_projects = sorted(load_projects(), key=lambda project: project.last_opened, reverse=True)
    return templates.TemplateResponse("projects_menu.html", {"request": request, "projects": sorted_projects})


@router.get("/add/new", response_class=HTMLResponse)
async def add_project_form(request: Request):
    return templates.TemplateResponse("add_project.html", {"request": request})


@router.post("/add/new")
async def add_project(title: str = Form(...)):
    project_dir = create_project_path(title)

    create_file_structure(project_dir)
    
    project_menu = ProjectMenuData(
        name=title,
        last_opened=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        path=project_dir
    )
    project = Project(
        name=title,
        characters_n=0,
        locations_n=0,
        llm=settings.default_llm,
        diffusion_model=settings.default_diffusion_model
    )
    
    add_project_data(project_menu)
    
    project_data_file = os.path.join(project_dir, "data", "project_data.json")
    with open(project_data_file, 'w') as file:
        json.dump(project.model_dump(), file, indent=4)
    
    return RedirectResponse(url='/project/'+title, status_code=303)
