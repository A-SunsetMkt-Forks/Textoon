#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import io

model_json_path = 'assets/model_configuration.json'
with open(model_json_path, 'r') as f:
    model_dict = json.load(f)
server_address = model_dict["comfyui_ip_port"]
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            # If you want to be able to decode the binary stream for latent previews, here is how you can do it:
            # bytesIO = BytesIO(out[8:])
            # preview_image = Image.open(bytesIO) # This is your preview in PIL image format, store it in a global
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        images_output = []
        if 'images' in node_output:
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
        output_images[node_id] = images_output

    return output_images

def call_comfyui_txt2img(prompt, control_image, ckpt_name):
    workflow_path = 'workflow/sdxl_txt2img_api.json'
    with open(workflow_path, 'r',encoding='utf-8') as f:
        workflow = json.load(f)
    
    workflow["10"]["inputs"]["ckpt_name"] = ckpt_name
    workflow["41"]["inputs"]["text"] = prompt

    workflow["53"]["inputs"]["image"] = control_image

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    images = get_images(ws, workflow)
    # print(images.keys())
    ws.close() # for in case this example is used in an environment where it will be repeatedly called, like in a Gradio app. otherwise, you'll randomly receive connection timeouts
    #Commented out code to display the output images:

    gen_image = Image.open(io.BytesIO(images["23"][0]))
    canny_image = Image.open(io.BytesIO(images["50"][0]))
    return gen_image, canny_image

    # gen_image_scaled = Image.open(io.BytesIO(images["38"][0]))

    # return gen_image, gen_image_scaled

if __name__ == "__main__":
    prompt = "1girl, 独奏，黑色麻花辫，粉色网格短袖，蓝色短裙"
    control_image_path = ""
    gen_image, gen_image_scaled = call_comfyui_txt2img(prompt, control_image_path)