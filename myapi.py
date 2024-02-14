import json
import os
import datetime
from fastapi import FastAPI, HTTPException, Request, Form
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

if(not os.path.exists(settings.projects_dir)):
    os.makedirs(settings.projects_dir)

load_user_settings()
app = FastAPI()
app.include_router(menu_router, prefix="/menu")
app.include_router(projects_router, prefix="/project")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/projects", StaticFiles(directory="projects"), name="projects")



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
