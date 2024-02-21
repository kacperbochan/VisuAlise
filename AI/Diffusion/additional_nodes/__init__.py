import os
import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import torch
import folder_paths
import numpy as np
from comfy.cli_args import args
from rembg import remove
import cv2

class RemoveBackground:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",)
        },}
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "remove_background"
    CATEGORY = "image"
        
    def remove_background(self, image):

        input = Image.fromarray(np.clip(255. * image.to("cpu").numpy().squeeze(), 0, 255).astype(np.uint8))
        output = remove(input)
        resoult = torch.from_numpy(np.array(output).astype(np.float32) / 255.0).unsqueeze(0)

        return (resoult,)

class SaveImageOutside:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "images": ("IMAGE", ),
                    "directory": ("STRING", {"default": "ComfyUI"}),
                    "filename": ("STRING", {"default": "ComfyUI"})},
                    "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }

    RETURN_TYPES = ()
    FUNCTION = "save_images_outside"

    OUTPUT_NODE = True

    CATEGORY = "image"

    def save_images_outside(self, images, directory="ComfyUI", filename="file", prompt=None, extra_pnginfo=None):
        results = list()
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            file = f"{filename}.png"
            
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                count = 1
                while os.path.isfile(file_path):
                    count += 1
                    file = f"{filename}_{count:05}.png"
                    file_path = os.path.join(directory, file)
            
            img.save(file_path, pnginfo=metadata, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "directory": directory,
                "type": self.type
            })

        return { "ui": { "images": results } }
    

NODE_CLASS_MAPPINGS = {
    "Save Image Outside": SaveImageOutside,
    "Remove Image Background": RemoveBackground
}
