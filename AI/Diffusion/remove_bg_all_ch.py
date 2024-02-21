import os
import json
import requests

with open('AI/Diffusion/remove_background.json', 'r') as f:
    data = json.load(f)
    
    
def start_queue(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode("utf-8")
    requests.post(URL, data=data)


URL = "http://127.0.0.1:8188/prompt"

ch_directory = 'projects\\alice\\images\\characters'
sp_directory = 'projects\\alice\\images\\sprites'

ch_directory = os.path.join(os.getcwd(), ch_directory)
sp_directory = os.path.join(os.getcwd(), sp_directory)

ch_file_list = os.listdir(ch_directory)
sp_file_list = os.listdir(sp_directory)

for file in ch_file_list:
    if file.endswith('.png'):
        if file not in sp_file_list:
            
            data["1"]["inputs"]["image"] = str(os.path.join(ch_directory, file))
            data["3"]["inputs"]["directory"] = str(sp_directory)
            data["3"]["inputs"]["filename"] = str(file.split('.')[0])
            
            print()
            print(data)
            
            start_queue(data)
