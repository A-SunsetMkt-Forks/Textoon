import os
import gradio as gr
import sys
import time
import logging
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from modules.text2live2d import text2live2d_model

# setting logging
timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
os.makedirs('outputs/logging', exist_ok=True)
log_filename = f"outputs/logging/{timestamp}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_safetensors_files(directory):
    if os.path.exists(directory):
        safetensors_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.safetensors'):
                    safetensors_files.append(file)
    else:
        safetensors_files = ['realcartoonXL_v7.safetensors',]
    return safetensors_files

def update_textbox(selected_prompt):
    return selected_prompt
def create_ui():
    default_text = "她将长发扎成两条俏皮的双马尾，中发修剪得干净利落，长刘海微微遮住额头，露出一双灵动的蓝色眼睛。她穿着一件圆领的浅紫色短袖上衣，袖口处有荷叶边设计，下身搭配一条高腰的白色短裤，脚上穿着一双白色运动鞋，整体造型充满青春气息。"
    example_prompts = [
        "她将长发扎成两条俏皮的双马尾，中发修剪得干净利落，长刘海微微遮住额头，露出一双灵动的蓝色眼睛。她穿着一件圆领的浅紫色短袖上衣，袖口处有荷叶边设计，下身搭配一条高腰的白色短裤，脚上穿着一双白色运动鞋，整体造型充满青春气息。",
        "She has long yellow hair and blue eyes. She is wearing a light green V-neck short-sleeved shirt with a small lamb pattern on the chest, a soft blue plaid skirt, and black short boots, showing the girl's playfulness and vitality.",
        "She has long flowing hair, dreamy lavender eyes, and elegant long bangs that slightly cover her forehead. She wears a pure white round-neck lace top with soft three-quarter sleeves, a light gray mid-length floral skirt, and beige mid-calf boots. The overall look is sweet and lovely, and the delicate embroidery on the hem adds a touch of romance.",
        "她留着一头柔顺的金色长发，发尾微微内卷，中发长度刚好及肩，搭配清爽的短刘海，露出一双明亮的棕色眼睛。她身穿一件高领的白色针织上衣，袖口处点缀着精致的蕾丝花纹，下身搭配一条黑白格子休闲长裤，脚上穿着一双蓝色平底鞋，整体造型既优雅又不失活力。",
        "她有着利落的短发，金色琥珀色的眼睛闪耀着智慧的光芒，利落的短刘海展现出自信与干练。穿着深黑色无领亚麻上衣，透气的无袖设计，配以棕色五分修身裤和时尚白色休闲鞋，整体造型时尚舒适，亚麻材质在阳光下泛着柔和的光泽。",
        "她留着蓬松的长双马尾，深邃的黑色眼睛中蕴含着神秘，整齐的中刘海勾勒出精致的眉眼。身穿酒红色方领针织上衣，优雅的九分袖，搭配亮黑色超短皮裙和漆皮短靴，整体造型性感魅力十足，针织上衣的细腻纹理与皮裙形成鲜明对比，突显个性。",
        "她拥有柔顺的长发，银灰色的眼睛透出冷静与高贵，飘逸的长刘海轻拂脸庞。穿着象牙白高领羊毛衫，厚实的半袖，配上深灰色熨烫整齐的长裤和光滑的黑色皮鞋，整体造型气质高贵，羊毛衫的纹理细腻丰富，散发出温暖的质感。",
        "她的中等长度头发，粉色玛瑙色的眼睛闪烁着可爱光辉，轻盈的短刘海增添了几分俏皮。身穿浅蓝色V领棉质上衣，舒适的短袖，搭配白色七分休闲裤和粉色运动鞋，整体搭配活力四射，棉质上衣的柔软质地与运动鞋的动感设计相得益彰。",
        "她留着飘逸的短双马尾，橙色琥珀色的眼睛充满热情，流畅的长刘海增添了几分神秘。穿着橄榄绿圆领绸缎上衣，优雅的长袖，配上深绿色中长A字裙和棕色中筒麂皮靴，整体造型优雅动人，绸缎上衣的光泽与裙摆的褶皱细节相映成趣。",
        "她拥有俏丽的短发，温暖的棕色眼睛中透出亲和力，整齐的中刘海勾勒出可爱的面庞。身穿卡其色方领棉衫，轻便的九分袖设计，搭配深蓝色短裤和灰色休闲鞋，整体造型休闲自在，棉衫的质地柔软，细节处的纽扣装饰别具一格。",
        "她将长发扎成两条活泼的双马尾，中发自然垂落在肩头，短刘海整齐地贴在额头上，露出一双明亮的橙色眼睛。她身穿一件无领的黄色短袖上衣，衣摆处有荷叶边设计，下身搭配一条牛仔短裙，脚上穿着一双白色运动鞋，整体造型充满了活力与朝气。"
    ]

    with gr.Blocks(title='Textoon',) as demo:
        gr.Markdown("# Textoon: Generating Vivid 2D Cartoon Characters from Text Descriptions")
        with gr.Row():
            with gr.Column(scale=1):
                dropdown = gr.Dropdown(choices=example_prompts, label="select a description text prompt")
                text_prompt = gr.Textbox(label="text prompt", value=default_text, interactive=True, visible=True)
                dropdown.change(fn=update_textbox, inputs=dropdown, outputs=text_prompt)
                request_number = gr.Dropdown(
                        label="request_number",
                        choices=[timestamp],
                        value=timestamp,
                        interactive=True
                    )
                with gr.Row():
                    ckpt_name = gr.Dropdown(
                        label="SDXL base model",
                        choices=['realcartoonXL_v7.safetensors','sdxl-动漫二次元_2.0.safetensors'],
                        value='realcartoonXL_v7.safetensors',
                        interactive=True
                    )
                    delight_bangs = gr.Dropdown(
                        label="remove bangs highlight",
                        choices=[False, True],
                        value=False,
                        interactive=True
                    )
                    translation_services = gr.Dropdown(
                        label="translation_services",
                        choices=["google", "aliyun"],
                        value='google',
                        interactive=True
                    )
                generate_button = gr.Button("生成图像")
                sd_image = gr.Image(type='pil', label="Generated image", image_mode='RGB', visible=True)
                save_folder = gr.Textbox(label="save folder", interactive=False)

            with gr.Column(scale=1):
                live2d_preview = gr.Image(type='pil', label="Generated Live2D Model", image_mode='RGB', visible=True, show_download_button=True, show_fullscreen_button=True)
                target_model_dir = gr.Textbox(label="Live2D Model", interactive=False)
                generate_button.click(fn=text2live2d_model, inputs=[text_prompt,request_number,ckpt_name,delight_bangs,translation_services], outputs=[sd_image, live2d_preview, save_folder, target_model_dir])
    
    demo.launch(server_name="0.0.0.0", server_port=7777)

if __name__ == "__main__":
    create_ui()