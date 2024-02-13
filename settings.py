import json
import os

class global_settings():
    projects_json_path = "projects.json"
    projects_dir = 'projects'
    llm_dir = 'AI\LLM'
    diffusion_dir = 'AI\Diffusion'
    
    
    def check_settings_file():
        settings_file = os.path.join(os.getcwd(), 'settings.json')

        if not os.path.exists(settings_file):
            # Create the settings file with default values
            default_settings = {
                "directories": {
                    "projects": global_settings.projects_dir,
                    "llm": global_settings.llm_dir,
                    "diffusion": global_settings.diffusion_dir
                }
            }
            with open(settings_file, 'w') as file:
                json.dump(default_settings, file, indent=4)
        else:
            # Read the existing settings file
            with open(settings_file, 'r') as file:
                try:
                    existing_settings = json.load(file)
                except json.JSONDecodeError:
                    # Handle invalid JSON format
                    print("Invalid JSON format in settings file.")
                    return

            # Validate and update the variables
            if "directories" in existing_settings:
                directories = existing_settings["directories"]
                if "projects" in directories:
                    if os.path.exists(directories["projects"]):
                        global_settings.projects_dir = directories["projects"]
                    else:
                        print("Invalid projects in settings file.")
                if "llm" in directories:
                    if os.path.exists(directories["llm"]):
                        global_settings.llm_dir = directories["llm"]
                    else:
                        print("Invalid llm in settings file.")
                if "diffusion" in directories:
                    if os.path.exists(directories["diffusion"]):
                        global_settings.diffusion_dir = directories["diffusion"]
                    else:
                        print("Invalid diffusion in settings file.")



