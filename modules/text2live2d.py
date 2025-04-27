import os
import json
import time
import shutil
from PIL import Image
from modules.prompt_parsing import parsing_prompt_to_partlist
from utils.image_process import pil_to_cv2, pil_to_base64
from modules.run_comfyui_txt2img import call_comfyui_txt2img
from utils.transfer_image_aspect_ratio import transfer_image_aspect_ratio_1half,restore_image_aspect_ratio
from utils.transfer_part_texture import combine_part_to_image, extract_part_to_texture, apply_eye_color, gen_image_with_combination
from modules.delight_bang import extract_hair_mask, delight_for_banghair
from modules.inpainting_occlusion import inpainting_long_backhair
import logging
logger = logging.getLogger(__name__)


def text2live2d_model(text_prompt,
                 request_number,
                 ckpt_name,
                 delight_bangs,
                 translation_services,
                 gen_leg=True):
    logger.info(f"input_parameters: \ntext_prompt:{text_prompt}\nrequest_number:{request_number}\nckpt_name:{ckpt_name}\ndelight_bangs:{delight_bangs}\ntranslation_services:{translation_services}")
    # Load base model configuration
    model_json_path = 'assets/model_configuration.json'
    with open(model_json_path, 'r') as f:
        model_config_dict = json.load(f)
    model_dict = model_config_dict['haimeng']

    # Parse the widget attribute eye color from the input prompt
    english_prompt, part_list, eye_color, judge_flag_dict, judge_type_dict = parsing_prompt_to_partlist(text_prompt, model_config_dict, translation_services)
    ponytail_flag, ponytail_type = judge_flag_dict['ponytail'], judge_type_dict['ponytail']
    
    # Set the folder to save the results of the run
    save_time_dir = os.path.join('outputs', request_number)
    os.makedirs(save_time_dir, exist_ok=True)

    # Control Image of component combination
    combination_image = combine_part_to_image(model_dict, part_list, judge_flag_dict, judge_type_dict, save_time_dir)
    combination_image_1half = transfer_image_aspect_ratio_1half(combination_image)
    combination_image_1half_resized = combination_image_1half.resize((1024, 1536), Image.LANCZOS)
    control_image_path = os.path.join(save_time_dir, "control_image.png")
    combination_image_1half_resized.save(control_image_path)
    control_image_base64_str = pil_to_base64(combination_image_1half_resized)

    # Generate preliminary image
    start_time = time.time()
    gen_image_wlight, canny_image = call_comfyui_txt2img(english_prompt, control_image_base64_str, ckpt_name)
    gen_image_wlight.save(os.path.join(save_time_dir, "gen_image.png"))
    canny_image.save(os.path.join(save_time_dir, "canny_image_txt2img.png"))
    end_time = time.time()
    logger.info(f"txt2img Time cost: {end_time - start_time}")

    # Remove hair highlights
    if delight_bangs:
        hair_mask_pil = extract_hair_mask(model_dict, part_list, ponytail_flag, ponytail_type)
        hair_mask_pil.save(os.path.join(save_time_dir, "hair_mask.png"))
        gen_image = delight_for_banghair(gen_image_wlight, combination_image_1half_resized, save_time_dir, hair_mask_pil)
    else:
        gen_image = gen_image_wlight
    # gen_image = call_comfyui_caption(caption_prompt, control_image_base64_str)

    # Combine to see the effect
    gen_image_combined = gen_image_with_combination(gen_image, model_dict, part_list, judge_flag_dict, judge_type_dict, eye_color, save_time_dir, gen_leg)
    sd_image_1half = transfer_image_aspect_ratio_1half(gen_image_combined)
    sd_image_1half_resized = sd_image_1half.resize((1024, 1536), Image.LANCZOS)
    sd_image_1half_resized.save(os.path.join(save_time_dir, "gen_image_combination.png"))
    
    if part_list[-1].startswith("trousers"):
        model_dict["lower_body"] = "trousers"
    else:
        model_dict["lower_body"] = "skirt"
    if ponytail_flag:
        model_dict["ponytail"] = ponytail_type
    
    # Restore to original size
    sd_image = sd_image_1half_resized
    gen_image_scaled_resized = sd_image.resize((3360, 5040), Image.LANCZOS)
    gen_image_origin_size = restore_image_aspect_ratio(gen_image_scaled_resized)
    gen_image_origin_size.save(os.path.join(save_time_dir, "gen_image_origin_size.png"))

    # Extract part texture and apply eye color
    extract_part_to_texture(model_dict, part_list, judge_flag_dict, judge_type_dict, gen_image_origin_size, save_time_dir)
    apply_eye_color(eye_color, model_dict, save_time_dir)

    # Repair occlusion
    if not ponytail_flag:
        gen_image_origin_size_cv2 = pil_to_cv2(gen_image_origin_size)
        start_time = time.time()
        backhair_repaired_pil = inpainting_long_backhair(gen_image_origin_size_cv2, model_dict, part_list, save_time_dir)
        end_time = time.time()
        logger.info(f"inpainting Time cost: {end_time - start_time}")
    
    # set live2d base model parameters
    texture_dir = os.path.join(save_time_dir, "texture")
    setparameter = {
                    "Param": 0,
                    "Param47": 1,
                    "Param48": 0,
                    "Param54": 0,
                    "Param57": 1,
                    "Param59": 1,
                    "Param60": 0
                    }
    if ponytail_flag:
        setparameter["Param"] = 0
    else:
        setparameter["Param"] = 1
    if model_dict["lower_body"] == "trousers":
        setparameter["Param54"] = 1
    else:
        setparameter["Param48"] = 1
    if judge_flag_dict['breast']:
        setparameter["Param60"] = 1
    code = 0

    # Packaged into a complete Live2D model
    target_model_dir = os.path.join(save_time_dir, os.path.basename(request_number)+"_model")
    if os.path.exists(target_model_dir):
        shutil.rmtree(target_model_dir)
    shutil.copytree(model_dict["model_dir"], target_model_dir)
    with open(os.path.join(target_model_dir,"config.json"), 'r') as json_file:
        model_config_data = json.load(json_file)
    model_config_data["setparameter"] = setparameter
    with open(os.path.join(target_model_dir,"config.json"), 'w') as json_file:
        json.dump(model_config_data, json_file, indent=4)
    for filename in os.listdir(texture_dir):
        if filename.endswith(".png"):
            src_file = os.path.join(texture_dir, filename)
            dst_file = os.path.join(target_model_dir, "female_01Arkit_6.4096", filename)
            if os.path.isfile(src_file):
                shutil.copy(src_file, dst_file)
    logger.info(f"Packaged into a complete Live2D model: {target_model_dir}")

    # record
    record_dict = {
        "request_number": request_number,
        "input_prompt": text_prompt,
        "text_prompt": english_prompt,
        "part_list": part_list,
        "eye_color": eye_color,
        "judge_flag": judge_flag_dict,
        "judge_type": judge_type_dict,
        "save_time_dir": save_time_dir,
        "control_image_path": control_image_path,
        "gen_image_path": os.path.join(save_time_dir, "gen_image.png"),
        "texture_dir": texture_dir,
        "setparameter": setparameter,
        "code": code
    }
    record_path = os.path.join(save_time_dir, "run_record.json")
    with open(record_path, 'w', encoding='utf-8') as json_file:
        json.dump(record_dict, json_file, ensure_ascii=False, indent=4)

    return sd_image_1half_resized, gen_image_combined, save_time_dir, target_model_dir