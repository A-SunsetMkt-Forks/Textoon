#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import io
import base64

model_json_path = 'assets/model_configuration.json'
with open(model_json_path, 'r') as f:
    model_dict = json.load(f)
server_address = model_dict["comfyui_ip_port"]
client_id = str(uuid.uuid4())

def pil_to_base64(image_pil):
    buffered = io.BytesIO()
    image_pil.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()
    image_base64_str = base64.b64encode(image_bytes).decode('utf-8')

    return image_base64_str

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

def get_texts(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_texts = {}
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
        if 'text' in list(node_output.keys()):
            # print(f'node_id: {node_id}, node_output:{node_output}')
            output_texts[node_id] = node_output['text']

    return output_texts

def call_comfyui_translate_toeng(chn_prompt):
    workflow_path = 'workflow/translate_chn2eng_api.json'
    with open(workflow_path, 'r',encoding='utf-8') as f:
        workflow = json.load(f)
    
    workflow["1"]["inputs"]["text"] = chn_prompt

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    texts = get_texts(ws, workflow)
    # print(texts.keys())
    ws.close() # for in case this example is used in an environment where it will be repeatedly called, like in a Gradio app. otherwise, you'll randomly receive connection timeouts
    #Commented out code to display the output images:

    text = texts["2"][0]
    return text

    # gen_image_scaled = Image.open(io.BytesIO(images["38"][0]))

    # return gen_image, gen_image_scaled

def call_comfyui_translate_tochn(chn_prompt):
    workflow_path = 'workflow/translate_eng2chn_api.json'
    with open(workflow_path, 'r',encoding='utf-8') as f:
        workflow = json.load(f)
    
    workflow["1"]["inputs"]["text"] = chn_prompt

    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    texts = get_texts(ws, workflow)
    # print(texts.keys())
    ws.close() # for in case this example is used in an environment where it will be repeatedly called, like in a Gradio app. otherwise, you'll randomly receive connection timeouts
    #Commented out code to display the output images:

    text = texts["2"][0]
    return text

    # gen_image_scaled = Image.open(io.BytesIO(images["38"][0]))

    # return gen_image, gen_image_scaled


if __name__ == "__main__":
    # from utils.image_base64 import pil_to_base64
    chn_prompt = "1girl, 独奏, 一个可爱的小女孩，黑色马尾，穿着蓝色校园jk短袖制服，搭配牛仔短裤，脚上是一双红色的运动鞋，过渡自然，影视动漫，4K，超高清"
    text = call_comfyui_translate_toeng(chn_prompt)
    print(text)