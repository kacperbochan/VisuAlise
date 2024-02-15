import json
import os

from models.models import ProgramSettings, LLM, DiffusionModel

#default_settings
global_settings: ProgramSettings = ProgramSettings(
    projects_dir = 'projects',
    llm_dir = 'AI\LLM',
    diffusion_dir = 'AI\Diffusion',
    theme='dark',
    
    default_llm = LLM(
        model="mistral-7b-instruct-v0.2.Q4_K_M.gguf", 
        temperature=0.7, 
        top_k=40, 
        top_p=0.9, 
        repetition_penalty=1.0, 
        max_length=100, 
        device="gpu"),
    
    default_diffusion_model = DiffusionModel(
        model="dreamshaper_8.safetensors", 
        steps=25, 
        temperature=0.7, 
        batch=4, 
        device="gpu")
)

#validate_user_settings
def load_user_settings():
    settings_file = os.path.join(os.getcwd(), 'settings.json')

    if not os.path.exists(settings_file):
        with open(settings_file, 'w') as file:
            json.dump(global_settings.model_dump(), file, indent=4)
    else:
        # Read the existing settings file
        with open(settings_file, 'r') as file:
            try:
                user_settings = json.load(file)
                if 'projects_dir' in user_settings and os.path.isdir(user_settings['projects_dir']):
                    global_settings.projects_dir = user_settings['projects_dir']
                if 'llm_dir' in user_settings and os.path.isdir(user_settings['llm_dir']):
                    global_settings.llm_dir = user_settings['llm_dir']
                if 'diffusion_dir' in user_settings and os.path.isdir(user_settings['diffusion_dir']):
                    global_settings.diffusion_dir = user_settings['diffusion_dir']
                if 'theme' in user_settings and os.path.isdir(user_settings['theme']):
                    global_settings.theme = user_settings['theme']
                if 'default_llm' in user_settings and isinstance(user_settings['default_llm'], LLM):
                    global_settings.default_llm = user_settings['default_llm']
                if 'default_diffusion_model' in user_settings and isinstance(user_settings['default_diffusion_model'], DiffusionModel):
                    global_settings.default_diffusion_model = user_settings['default_diffusion_model']
            except json.JSONDecodeError:
                # Handle invalid JSON format
                print("Invalid JSON format in settings file.")
                return

if __name__ == "__main__":
    load_user_settings()
    print(f"Projects directory: {global_settings.projects_dir}")
    print(f"LLM directory: {global_settings.llm_dir}")
    print(f"Diffusion directory: {global_settings.diffusion_dir}")
    print(f"Theme: {global_settings.theme}")
    print(f"Default LLM: {global_settings.default_llm}")
    print(f"Default Diffusion Model: {global_settings.default_diffusion_model}")