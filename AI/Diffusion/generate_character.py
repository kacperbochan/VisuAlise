import os
import json
import requests

with open('data.json', 'r') as f:
    data = json.load(f)['nodes']
    
    
def start_queue(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode("utf-8")
    requests.post(URL, data=data)


URL = "http://127.0.0.1:8188/prompt"

print(data)
    
start_queue(data)
