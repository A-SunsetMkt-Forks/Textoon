import os
import time
import logging
import argparse
from modules.text2live2d import text2live2d_model

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

def text2live2d(input_parameters):
    # Parse input parameters
    text_prompt = input_parameters['text_prompt']
    request_number = input_parameters['request_number']
    ckpt_name = input_parameters['ckpt_name']
    delight_bangs = input_parameters['delight_bangs']
    translation_services = input_parameters['translation_services']

    sd_image_1half_resized, gen_image_combined, save_time_dir, target_model_dir = text2live2d_model(text_prompt,
                                                                                                    request_number,
                                                                                                    ckpt_name,
                                                                                                    delight_bangs,
                                                                                                    translation_services)

    return target_model_dir


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process text2live2d parameters.')

    # add setting parameters
    parser.add_argument('--text_prompt', type=str, default="她将长发扎成两条俏皮的双马尾，中发修剪得干净利落，长刘海微微遮住额头，露出一双灵动的蓝色眼睛。她穿着一件圆领的浅紫色短袖上衣，袖口处有荷叶边设计，下身搭配一条高腰的白色短裤，脚上穿着一双白色运动鞋，整体造型充满青春气息。", help='input text prompt')
    parser.add_argument('--request_number', type=str, default=None, help='mark the request')
    parser.add_argument('--ckpt_name', type=str, default="realcartoonXL_v7.safetensors", help='SDXL Base Model for cartoon style')
    parser.add_argument('--delight_bangs', action='store_true', help='remove bangs highlight')
    parser.add_argument('--translation_services', type=str, default="google", help='translation services')
    args = parser.parse_args()

    request_number = args.request_number if args.request_number else timestamp
    input_parameters = {"text_prompt": args.text_prompt,  
                                "request_number": request_number,
                                "ckpt_name": args.ckpt_name,
                                "delight_bangs": args.delight_bangs,
                                "translation_services": args.translation_services,
                                }

    target_model_dir = text2live2d(input_parameters)
    logger.info(f'Generated model path: {target_model_dir}')
    
    
    