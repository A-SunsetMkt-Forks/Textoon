import cv2
import os
import json
import numpy as np
from PIL import Image
import os
import sys

current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from modules.run_comfyui_img2img import call_comfyui_img2img
from utils.image_process import alpha_to_rgb, pil_to_cv2, pil_to_mask, alphapil_to_mask, cv2_to_base64
import logging

logger = logging.getLogger(__name__)

def calc_max_y(sd_part_mask):
    height, width = sd_part_mask.shape
    max_y = 0

    for x in range(width):
        white_indices = np.where(sd_part_mask[:, x] == 255)[0]
        if white_indices.size > 0:
            max_y = max(max_y, white_indices.max())

    # logger.info(f"The maximum value of the pure white area in the vertical y direction is: {max_y}")
    return max_y

def image_mask_to_alpha(image_pil, mask_gray):
    alpha = Image.fromarray(mask_gray)
    alpha = alpha.point(lambda p: 255 if p > 0 else 0)
    image_pil.putalpha(alpha)
    return image_pil

def round_up_to_nearest_8(n):
    if n % 8 == 0:
        return n
    else:
        return n + (8 - n % 8)

def occlusion_handling(sd_part, sd_part_mask, inpaint_mask_enlarge, cut_off=False):
    """
    sd_part: 带有不透明度的SD生成的部件图像
    sd_part_mask: SD生成的部件的mask,灰度图
    inpaint_mask_enlarge: 遮挡前部区域,灰度图
    template_part: 部件原画用于产出图生图的canny
    """
    # Fill the inpaint area with adjacent pixels
    height, width = sd_part.shape[:2]
    for i in range(height):
        mask_2_row = inpaint_mask_enlarge[i, :]
        
        if np.any(mask_2_row):
            mask_1_row = sd_part_mask[i, :]

            valid_pixels = sd_part[i, :][(mask_1_row > 0) & (mask_2_row == 0)]
            
            if len(valid_pixels) > 0:
                mean_value = valid_pixels.mean(axis=0).astype(int)
                sd_part[i, mask_2_row > 0] = mean_value
    
    if cut_off:
        max_y = calc_max_y(sd_part_mask)
        y_line = int(max_y * 0.5)
        # logger.info(f'y_line: {y_line}')
        if y_line < sd_part.shape[0]:
            mean_pixels = []
            for x in range(sd_part.shape[1]):
                if sd_part_mask[y_line, x] > 0:
                    mean_pixels.append(sd_part[y_line, x])

            if mean_pixels:
                mean_color = np.mean(mean_pixels, axis=0)
            else:
                # logger.info("No pixels within the mask area are found in line y_line.")
                mean_color = (0, 0, 0)
        else:
            # logger.info("y_line exceeds the image extents.")
            mean_color = (0, 0, 0)

        for y in range(sd_part.shape[0]):
            if y > y_line:
                for x in range(sd_part.shape[1]):
                    if sd_part_mask[y, x] > 0:
                        sd_part[y, x] = mean_color
    
    return sd_part

def backhair_part_mask(model_dict, keyname, part_list):
    x = model_dict["photo"]["long_back_hair"]["x"]
    y = model_dict["photo"]["long_back_hair"]["y"]
    w = model_dict["photo"]["long_back_hair"]["w"]
    h = model_dict["photo"]["long_back_hair"]["h"]

    bang_mask = None
    for image_filename in part_list:
        if keyname in image_filename:
            part_path = model_dict["part_path"]
            bang_selected_path = os.path.join(part_path, image_filename)
            bang_selected_pil = Image.open(bang_selected_path)
            bang_mask_originsize = alphapil_to_mask(bang_selected_pil)

            origin_image = np.zeros((model_dict["psd_size"]["h"], model_dict["psd_size"]["w"]), dtype=np.uint8)
            part_name = image_filename[:image_filename.rfind("_")]
            x_s = model_dict["photo"][part_name]["x"]
            y_s = model_dict["photo"][part_name]["y"]
            w_s = model_dict["photo"][part_name]["w"]
            h_s = model_dict["photo"][part_name]["h"]
            origin_image[y_s:y_s+h_s, x_s:x_s+w_s] = bang_mask_originsize

            bang_mask = origin_image[y:y+h, x:x+w]
    
    return bang_mask
def inpainting_long_backhair(gen_image_cv2, model_dict, part_list, save_time_dir):
    long_backhair_template_pil = Image.open(os.path.join(model_dict["part_path"], "long_back_hair_0.png"))
    long_backhair_template_pil_rgb = alpha_to_rgb(long_backhair_template_pil)
    long_backhair_template_cv2 = pil_to_cv2(long_backhair_template_pil_rgb)
    # Extract the back hair region
    part_path = model_dict["part_path"]
    backhair_selected_path = os.path.join(part_path, part_list[0])

    backhair_selected_pil = Image.open(backhair_selected_path)
    backhair_selected_pil_rgb = alpha_to_rgb(backhair_selected_pil)
    backhair_selected_mask_cv2 = pil_to_mask(backhair_selected_pil_rgb)
    cv2.imwrite(os.path.join(save_time_dir, "backhair_template_mask_cv2.png"), backhair_selected_mask_cv2)
    # logger.info(np.unique(backhair_selected_mask_cv2))
    # Repair the back hair area
    x = model_dict["photo"]["long_back_hair"]["x"]
    y = model_dict["photo"]["long_back_hair"]["y"]
    w = model_dict["photo"]["long_back_hair"]["w"]
    h = model_dict["photo"]["long_back_hair"]["h"]

    gen_backhair_image = gen_image_cv2[y:y+h, x:x+w]

    gen_backhair_image_extracted = cv2.bitwise_and(gen_backhair_image, gen_backhair_image, mask=backhair_selected_mask_cv2)
    cv2.imwrite(os.path.join(save_time_dir, "gen_backhair_image_extracted.png"), gen_backhair_image_extracted)

    skin_pil = Image.open(model_dict["basemap_path"])
    skin_pil_crop = skin_pil.crop((x, y, x+w, y+h))
    skin_mask = alphapil_to_mask(skin_pil_crop)

    bang_mask = backhair_part_mask(model_dict, "bang", part_list)
    left_middle_hair_mask = backhair_part_mask(model_dict, "left_middle_hair", part_list)
    right_middle_hair_mask = backhair_part_mask(model_dict, "right_middle_hair", part_list)

    combined_mask = cv2.bitwise_and(backhair_selected_mask_cv2, skin_mask)

    neg_left_middle_hair_mask = cv2.bitwise_not(left_middle_hair_mask)
    neg_right_middle_hair_mask = cv2.bitwise_not(right_middle_hair_mask)
    neg_bang_mask = cv2.bitwise_not(bang_mask)

    result_mask = cv2.bitwise_and(combined_mask, neg_left_middle_hair_mask)
    result_mask = cv2.bitwise_and(result_mask, neg_right_middle_hair_mask)
    result_mask = cv2.bitwise_and(result_mask, neg_bang_mask)
    cv2.imwrite(os.path.join(save_time_dir, "result_mask.png"), result_mask)
    occlusion_mask = result_mask
    
    cv2.imwrite(os.path.join(save_time_dir, "occlusion_mask.png"), occlusion_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))
    occlusion_mask_enlarge = cv2.dilate(occlusion_mask, kernel, iterations=1)
    # logger.info(f'occlusion_mask_enlarge: {np.unique(occlusion_mask_enlarge)}')
    cv2.imwrite(os.path.join(save_time_dir, "occlusion_mask_enlarge.png"), occlusion_mask_enlarge)

    after_filling_image = occlusion_handling(gen_backhair_image, backhair_selected_mask_cv2, occlusion_mask_enlarge, True)
    cv2.imwrite(os.path.join(save_time_dir, "after_filling_image.png"), after_filling_image)
    after_filling_image_extracted = cv2.bitwise_and(after_filling_image, after_filling_image, mask=backhair_selected_mask_cv2)
    cv2.imwrite(os.path.join(save_time_dir, "after_filling_image_extracted.png"), after_filling_image_extracted)

    w_e = round_up_to_nearest_8(w)
    h_e = round_up_to_nearest_8(h)
    mask_expand_cv2 = cv2.copyMakeBorder(backhair_selected_mask_cv2, 0, h_e-h, 0, w_e-w, cv2.BORDER_CONSTANT, value=(0))
    image_expand_cv2 = cv2.copyMakeBorder(after_filling_image_extracted, 0, h_e-h, 0, w_e-w, cv2.BORDER_CONSTANT, value=(0,0,0))
    image_base64 = cv2_to_base64(image_expand_cv2)
    mask_base64 = cv2_to_base64(mask_expand_cv2)
    template_control_image = cv2.imread(os.path.join(model_dict["occlusion_dir"], "long_back_hair_template_control.png"))
    template_control_selected = cv2.bitwise_and(template_control_image, template_control_image, mask=backhair_selected_mask_cv2)
    template_control_selected_expand = cv2.copyMakeBorder(template_control_selected, 0, h_e-h, 0, w_e-w, cv2.BORDER_CONSTANT, value=(0,0,0))
    template_control_base64 = cv2_to_base64(template_control_selected_expand)

    template_joy_image = cv2.imread(os.path.join(model_dict["occlusion_dir"], "long_back_hair_template.png"))
    template_joy_selected = cv2.bitwise_and(template_joy_image, template_joy_image, mask=backhair_selected_mask_cv2)
    template_joy_selected_expand = cv2.copyMakeBorder(template_joy_selected, 0, h_e-h, 0, w_e-w, cv2.BORDER_CONSTANT, value=(0,0,0))
    template_joy_base64 = cv2_to_base64(template_joy_selected_expand)

    gen_image_expand_pil = call_comfyui_img2img(template_control_base64, template_joy_base64, image_base64, mask_base64)
    gen_image_pil = gen_image_expand_pil.crop((0,0,w,h))
    gen_image_pil.save(os.path.join(save_time_dir, "gen_image_pil.png"))

    gen_image_alpha = image_mask_to_alpha(gen_image_pil, backhair_selected_mask_cv2)
    gen_image_alpha.save(os.path.join(save_time_dir, "gen_image_alpha.png"))

    texture_path = os.path.join(save_time_dir, "texture", model_dict["texture"]["long_back_hair"]["name"]+".png")
    texture_pil = Image.open(texture_path)
    texture_pil.paste(gen_image_alpha, (model_dict["texture"]["long_back_hair"]["x"], model_dict["texture"]["long_back_hair"]["y"]))
    texture_pil.save(os.path.join(save_time_dir, "texture", model_dict["texture"]["long_back_hair"]["name"]+".png"))
    return gen_image_alpha

if __name__ == "__main__":
    # bang_path = "assets/haimeng/part/bang_hair_0.png"
    # bang_img = Image.open(bang_path)
    # bang_img_pil = alpha_to_rgb(bang_img)
    # bang_img_cv2 = pil_to_cv2(bang_img_pil)

    # left_middle_hair_path = "assets/haimeng/part/left_middle_hair_0.png"
    # left_middle_hair_img = Image.open(left_middle_hair_path)
    # left_middle_hair_img_pil = alpha_to_rgb(left_middle_hair_img)
    # left_middle_hair_img_cv2 = pil_to_cv2(left_middle_hair_img_pil)

    # right_middle_hair_path = "assets/haimeng/part/right_middle_hair_0.png"
    # right_middle_hair_img = Image.open(right_middle_hair_path)
    # right_middle_hair_img_pil = alpha_to_rgb(right_middle_hair_img)
    # right_middle_hair_img_cv2 = pil_to_cv2(right_middle_hair_img_pil)

    model_json_path = 'assets/haimeng/haimeng_standard.json'
    with open(model_json_path, 'r') as f:
        model_dict = json.load(f)

    # parsing prompt to part list
    part_list = ["long_back_hair_0.png", "left_middle_hair_0.png", "right_middle_hair_0.png", "bang_hair_0.png", 
                 "left_long_sleeve_0.png", "right_long_sleeve_0.png", "turtleneck_shirt_4.png", 
                 "left_boot_1.png", "right_boot_1.png", "skirt_4.png"]
    
    save_time_dir = "outputs/20241127/20241127-193516"

    gen_image_origin_size = cv2.imread("outputs/20241127/20241127-193516/gen_image_origin_size.png")

    gen_image_alpha = inpainting_long_backhair(gen_image_origin_size, model_dict, part_list, save_time_dir)