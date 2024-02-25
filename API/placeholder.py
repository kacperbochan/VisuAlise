
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
