import time
import os
import io
import json
import base64
import sys
import shutil
import cv2
from PIL import Image
import numpy as np
from utils.image_process import cv2_to_pil,pil_to_cv2

def crop_center(img, crop_x, crop_y):
    y, x, _ = img.shape
    start_x = x // 2 - (crop_x // 2)
    start_y = 0
    return img[start_y:start_y + crop_y, start_x:start_x + crop_x]

def fill_pixel_for_banghair(image):
    # Scalloped Highlights to Fill Bangs
    center = (254, 16)
    radius1 = 65
    radius2 = 100

    x_min, x_max = 213, 306
    y_min, y_max = 58, 124

    result_image = image.copy()

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            distance = np.sqrt((x - center[0])**2 + (y - center[1])**2)
            if radius1 < distance < radius2:
                direction = np.array([x - center[0], y - center[1]])
                direction = direction / np.linalg.norm(direction)

                inner_point = center + direction * radius1
                outer_point = center + direction * radius2

                inner_point = np.round(inner_point).astype(int)
                outer_point = np.round(outer_point).astype(int)

                for channel in range(3):
                    inner_value = image[inner_point[1], inner_point[0], channel]
                    outer_value = image[outer_point[1], outer_point[0], channel]

                    t = (distance - radius1) / (radius2 - radius1)
                    interpolated_value = (1 - t) * inner_value + t * outer_value

                    result_image[y, x, channel] = int(interpolated_value)
    return result_image

def extract_hair_mask(model_dict, part_list, ponytail_flag, ponytail_type):
    basemap_path = model_dict["basemap_path"]
    basemap_image = Image.open(basemap_path)
    part_dir = model_dict["part_path"]

    width, height = basemap_image.size
    gray = Image.new("L", (width, height), 0)

    # ponytail
    image1_list = []
    image3_list = []
    if ponytail_flag:
        if ponytail_type == "double":
            # image1_list = model_dict["atts_map"]["hair length"]["double-ponytail"]
            image1_list = model_dict["atts_map"]["hair length"]["double ponytail"]
            image3_list = model_dict["atts_map"]["bang type"]["ponytail"]
        else:
            # image1_list = model_dict["atts_map"]["hair length"]["half-ponytail"]
            image1_list = model_dict["atts_map"]["hair length"]["half up ponytail"]
            image3_list = model_dict["atts_map"]["bang type"]["ponytail"]
    else:
        for part in part_list:
            if "long_back" in part:
                image1_list.append(part)
            elif "middle" in part or "bang" in part:
                image3_list.append(part)

    image1 = Image.new("RGBA", basemap_image.size, (0, 0, 0, 0))
    image3 = Image.new("RGBA", basemap_image.size, (0, 0, 0, 0))
    for image1_name in image1_list:
        part = Image.open(os.path.join(part_dir, image1_name))
        part_name = image1_name[:image1_name.rfind("_")]
        x = model_dict["photo"][part_name]["x"]
        y = model_dict["photo"][part_name]["y"]

        image1.paste(part, (x, y))
    for image3_name in image3_list:
        part = Image.open(os.path.join(part_dir, image3_name))
        part_name = image3_name[:image3_name.rfind("_")]
        x = model_dict["photo"][part_name]["x"]
        y = model_dict["photo"][part_name]["y"]

        image3.paste(part, (x, y))
    
    image2 = basemap_image
    gray_array = np.array(gray)
    alpha1 = np.array(image1.split()[-1])
    gray_array[alpha1 > 0] = 255

    alpha2 = np.array(image2.split()[-1])
    gray_array[alpha2 > 0] = 0

    alpha3 = np.array(image3.split()[-1])
    gray_array[alpha3 > 0] = 255

    mask_pil = Image.fromarray(gray_array)
    cropped_image = mask_pil.crop((0, 404, 2951, 5444))
    new_image = Image.new('L', (3360, 5040), (0))

    new_image.paste(cropped_image, (205, 0))
    gray_1024 = new_image.resize((1024, 1536), Image.LANCZOS)

    return gray_1024

def delight_for_banghair(gen_image, control_combination, save_time_dir, hair_mask_pil=None):
    image_cv2 = pil_to_cv2(gen_image)
    mask = cv2.imread('assets/haimeng/delight/hair_delight_512_mask_3.png', 0)
    addcanny_edge = cv2.imread('assets/haimeng/delight/hair_delight_512_addcanny_5.png', 0)

    control_combination_cv2 = pil_to_cv2(control_combination)

    crop_size = (512, 512)
    cropped_image = crop_center(image_cv2, *crop_size)
    cv2.imwrite(os.path.join(save_time_dir, 'gen_image_512.png'), cropped_image)
    cropped_control_combination = crop_center(control_combination_cv2, *crop_size)
    gray_control_combination = cv2.cvtColor(cropped_control_combination, cv2.COLOR_BGR2GRAY)

    inpainted_image = fill_pixel_for_banghair(cropped_image)
    cv2.imwrite(os.path.join(save_time_dir, "hair_inpainted.png"), inpainted_image)

    crop_y, crop_x, _ = cropped_image.shape
    y, x, _ = image_cv2.shape
    start_x = x // 2 - (crop_x // 2)
    start_y = 0
    image_cv2[start_y:start_y + crop_y, start_x:start_x + crop_x] = inpainted_image

    gen_image_delighted_pil = cv2_to_pil(image_cv2)
    save_delighted_path = os.path.join(save_time_dir, "gen_image_delighted.png")
    gen_image_delighted_pil.save(save_delighted_path)

    if hair_mask_pil is not None:
        hair_mask_np = np.array(hair_mask_pil)
        white_mask = hair_mask_np == 255
        hsv_image = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2HSV)
        v_channel = hsv_image[:, :, 2]
        masked_v = v_channel[white_mask]
        average_brightness = np.mean(masked_v) if masked_v.size > 0 else 0

        brightness_threshold = 100
        if average_brightness < brightness_threshold:
            brightness_increase = 40
            v_channel[white_mask] = np.clip(v_channel[white_mask] + brightness_increase, 0, 255)
        hsv_image[:, :, 2] = v_channel

        image_cv2 = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2BGR)

        gen_image_delighted_enlight_pil = cv2_to_pil(image_cv2)
        save_delighted_enlight_path = os.path.join(save_time_dir, "gen_image_delighted_enlight.png")
        gen_image_delighted_enlight_pil.save(save_delighted_enlight_path)
        return gen_image_delighted_enlight_pil
    else:
        return gen_image_delighted_pil