import os
import socket
import uvicorn
import subprocess
import shutil
import yaml
from settings import global_settings, load_user_settings

def check_comfy():
    comfy_dir =  "./repositories/ComfyUI-master"
    return os.path.isdir(comfy_dir)

def check_additional_nodes():
    target_dir = "./repositories/ComfyUI-master/custom_nodes/additional_nodes"
    return os.path.isdir(target_dir)

def import_comfy():
    comfy_repo = "https://github.com/comfyanonymous/ComfyUI"
    comfy_dir = "repositories/ComfyUI-master"

    subprocess.run(["git", "clone", comfy_repo, comfy_dir])

def ensure_model_paths():
    extra_modules_file = "repositories/ComfyUI-master/extra_model_paths.yaml.example"
    if(not os.path.isfile(extra_modules_file)):
        return 
    
    new_file_name = "repositories/ComfyUI-master/extra_model_paths.yaml"
    os.rename(extra_modules_file, new_file_name)

def update_model_paths():
    extra_modules_file = "repositories/ComfyUI-master/extra_model_paths.yaml"
    with open(extra_modules_file, 'r') as file:
        data = yaml.safe_load(file)
    
    load_user_settings()
        
    data['a111']['base_path'] = "C:\\Users\\kacpe\\AI\\SD\\stable-diffusion-webui\\"
    
    with open(extra_modules_file, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

def copy_additional_nodes():
    source_dir = "./AI/Diffusion/additional_nodes"
    target_dir = "./repositories/ComfyUI-master/custom_nodes/additional_nodes"

    shutil.copytree(source_dir, target_dir)


def find_available_port(start_port):
    port = start_port
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except socket.error:
            port += 1

if __name__ == "__main__":
    
    if(not check_comfy()):
        import_comfy()
    
    if(not check_additional_nodes()):
        copy_additional_nodes()
    
    ensure_model_paths()
    
    update_model_paths()
    
    port = find_available_port(8000)
    uvicorn.run("myapi:app", host="127.0.0.1", port=port, reload=True)
