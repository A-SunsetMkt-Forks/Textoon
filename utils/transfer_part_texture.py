import os
import json
import time
import numpy as np
import colorsys
import sys
from PIL import Image
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)
from utils.transfer_image_aspect_ratio import restore_image_aspect_ratio
import logging

logger = logging.getLogger(__name__)

def get_distinct_colors(num_colors):
    hsv_colors = [(i / num_colors, 1, 1) for i in range(num_colors)]
    rgb_colors = [colorsys.hsv_to_rgb(*hsv) for hsv in hsv_colors]
    rgb_colors = [(int(r * 255), int(g * 255), int(b * 255)) for r, g, b in rgb_colors]
    return rgb_colors

def merge_breast_image(image, breast_image):
    assert image.size == breast_image.size, "image size must be equal to breast_image size"

    rect1 = (0, 300, 105, 960)  # (x1, y1, x2, y2)
    rect2 = (633, 300, 750, 960)  # (x1, y1, x2, y2)

    region1 = breast_image.crop(rect1)
    region2 = breast_image.crop(rect2)

    image.paste(region1, rect1[:2], region1)
    image.paste(region2, rect2[:2], region2)

    return image

def repair_sleeve_defects(right_sleeve_long, boundary_mask, offset=20):
    right_sleeve_case_img = right_sleeve_long
    boundary_mask_img = boundary_mask

    right_sleeve_case_data = np.array(right_sleeve_case_img)
    alpha_channel = right_sleeve_case_data[:, :, 3]

    mask = np.where(alpha_channel == 0, 0, 255).astype(np.uint8)
    boundary_mask_data = np.array(boundary_mask_img)

    for y in range(boundary_mask_data.shape[0]):
        row = boundary_mask_data[y, :]
        transitions = np.where(np.diff(row) != 0)[0]
        for x in transitions:
            if x-offset >= 0 and x+offset < boundary_mask_data.shape[1]:
                if mask[y, x-offset] == 255 and mask[y, x+offset] == 255:
                    for channel in range(4):
                        start_val = right_sleeve_case_data[y, x-offset, channel]
                        end_val = right_sleeve_case_data[y, x+offset, channel]
                        right_sleeve_case_data[y, x-offset:x+offset+1, channel] = np.interp(
                            range(x-offset, x+offset+1), [x-offset, x+offset], [start_val, end_val])

    result_img = Image.fromarray(right_sleeve_case_data, mode="RGBA")

    return result_img

def combine_part_to_image(model_dict, part_list, judge_flag_dict, judge_type_dict, save_time_dir):
    part_dir = model_dict["part_path"]

    basemap_path = model_dict["basemap_path"]
    basemap_image = Image.open(basemap_path)
    combined_image = Image.new("RGBA", basemap_image.size, (0, 0, 0, 0))
    # gen different color for each part
    rgb_colors_list = get_distinct_colors(3)
    color_mapping = {
        "left_long_sleeve": rgb_colors_list[0],
        "right_long_sleeve": rgb_colors_list[0],
        "turtleneck_shirt": rgb_colors_list[0],
        "left_boot": rgb_colors_list[1],
        "right_boot": rgb_colors_list[1],
        "skirt": rgb_colors_list[2],
        "trousers": rgb_colors_list[2]
    }
    for (i,image_filename) in enumerate(part_list):
        breast_flag, breast_type = judge_flag_dict['breast'], judge_type_dict['breast']
        image = Image.open(os.path.join(part_dir, image_filename))
        if breast_flag and image_filename.startswith("turtleneck_shirt"):
            breast_name = breast_type + " breast"
            breast_image_filename = model_dict["atts_map"]["breast type"][breast_name][0]
            breast_image = Image.open(os.path.join(part_dir, breast_image_filename))
            image = merge_breast_image(image, breast_image)

        part_name = image_filename[:image_filename.rfind("_")]
        if part_name in list(color_mapping.keys()):
            fill_color = color_mapping[part_name]

            data = np.array(image)
            alpha_channel = data[:, :, 3]
            opaque_mask = alpha_channel > 0
            data[opaque_mask] = [fill_color[0], fill_color[1], fill_color[2], 255]
            image = Image.fromarray(data, 'RGBA')

            if breast_flag and part_name.startswith("turtleneck_shirt"):
                breast_canny_name = breast_image_filename.replace('.png', '_canny.png')
                breast_canny_image = Image.open(os.path.join(part_dir, breast_canny_name))
                image = Image.alpha_composite(image, breast_canny_image)

        x = model_dict["photo"][part_name]["x"]
        y = model_dict["photo"][part_name]["y"]
        
        transparent_layer = Image.new("RGBA", basemap_image.size, (0, 0, 0, 0))
        transparent_layer.paste(image, (x, y))
        
        combined_image = Image.alpha_composite(combined_image, transparent_layer)
        if i < 1:
            transparent_layer = Image.new("RGBA", basemap_image.size, (0, 0, 0, 0))
            transparent_layer.paste(basemap_image, (0, 0))

            combined_image = Image.alpha_composite(combined_image, transparent_layer)
    
    combined_image.save(os.path.join(save_time_dir, "combination.png"))

    return combined_image


def extract_pixel_for_combination(a_image, b_image, px, py):
    a_image_with_alpha = a_image.convert('RGBA')
    a_pixels = a_image_with_alpha.load()
    b_pixels = b_image.load()
    b_width, b_height = b_image.size

    result = Image.new('RGBA', b_image.size)

    for x in range(b_width):
        for y in range(b_height):
            b_pixel = b_pixels[x, y]
            if b_pixel[3] > 0:
                a_x = px + x
                a_y = py + y
                a_pixel = a_pixels[a_x, a_y]
                result.putpixel((x, y), (a_pixel[0], a_pixel[1], a_pixel[2], b_pixel[3]))
            else:
                result.putpixel((x, y), b_pixel)
    
    return result

def gen_image_with_combination(gen_image, model_dict, part_list, judge_flag_dict, judge_type_dict, eye_color, save_time_dir, gen_leg):
    # restore to original size
    gen_image_scaled_resized = gen_image.resize((3360, 5040), Image.LANCZOS)
    gen_image_origin_size = restore_image_aspect_ratio(gen_image_scaled_resized)

    # basemap
    basemap_noeye = Image.open(model_dict["combination_basemap_path"]).convert("RGBA")
    basemap_addeye = Image.open(model_dict["combination_basemap_addeye_path"]).convert("RGBA")

    # add eye
    side_list = ["left","right"]
    for side in side_list:
        x = model_dict["eye_photo"][side]["x"]
        y = model_dict["eye_photo"][side]["y"]
        eye_template = os.path.join(model_dict["eye_dir"], side+"_"+eye_color+"_eye.png")
        if os.path.exists(eye_template):
            eye_image = Image.open(eye_template).convert("RGBA")
            basemap_noeye.paste(eye_image, (x, y), eye_image)
        else:
            logger.warning('eye template not found')
    basemap_noeye.save(os.path.join(save_time_dir, "witheye.png"))
    basemap_noeye.paste(basemap_addeye, (0, 0), basemap_addeye)

    combined_image = Image.new("RGBA", basemap_noeye.size, (0, 0, 0, 0))

    part_dir = model_dict["part_path"]
    if gen_leg:
        # add leg part
        leg_part_list = ["left_calf_0.png", "left_thigh_0.png", "right_calf_0.png", "right_thigh_0.png"]
        index = next((i for i, item in enumerate(part_list) if item.startswith('turtleneck_shirt')), None)
        if index is not None:
            part_list[index+1:index+1] = leg_part_list
        
        logger.info(f'part_list with leg:{part_list}')
    for (i,image_filename) in enumerate(part_list):
        breast_flag, breast_type = judge_flag_dict['breast'], judge_type_dict['breast']
        image = Image.open(os.path.join(part_dir, image_filename))
        if breast_flag and image_filename.startswith("turtleneck_shirt"):
            breast_name = breast_type + " breast"
            breast_image_filename = model_dict["atts_map"]["breast type"][breast_name][0]
            breast_image = Image.open(os.path.join(part_dir, breast_image_filename))
            image = merge_breast_image(image, breast_image)
        part_name = image_filename[:image_filename.rfind("_")]

        px = model_dict["photo"][part_name]["x"]
        py = model_dict["photo"][part_name]["y"]

        image_fill = extract_pixel_for_combination(gen_image_origin_size, image, px, py)
        
        transparent_layer = Image.new("RGBA", basemap_noeye.size, (0, 0, 0, 0))
        transparent_layer.paste(image_fill, (px, py))
        
        combined_image = Image.alpha_composite(combined_image, transparent_layer)
        if i < 1:
            transparent_layer = Image.new("RGBA", basemap_noeye.size, (0, 0, 0, 0))
            transparent_layer.paste(basemap_noeye, (0, 0))

            combined_image = Image.alpha_composite(combined_image, transparent_layer)
    
    combined_image.save(os.path.join(save_time_dir, "combination_with_generation.png"))
    return combined_image

def extract_part_to_texture(model_dict, part_list, judge_flag_dict, judge_type_dict, gen_image_origin_size, save_time_dir):
    part_dir = model_dict["part_path"]

    map_to_texture = {key: value["name"] for key, value in model_dict["texture"].items()}
    used_texture_list = []
    target_texture_list = []

    texture_00_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_00.png")).convert("RGBA")
    texture_01_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_01.png")).convert("RGBA")
    texture_02_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_02.png")).convert("RGBA")
    texture_03_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_03.png")).convert("RGBA")
    texture_04_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_04.png")).convert("RGBA")
    texture_05_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_05.png")).convert("RGBA")
    texture_07_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_07.png")).convert("RGBA")
    texture_08_image = Image.open(os.path.join(model_dict["texture_folder"],"texture_08.png")).convert("RGBA")
    
    texture_dict = {
            "texture_00": texture_00_image,
            "texture_01": texture_01_image,
            "texture_02": texture_02_image,
            "texture_03": texture_03_image,
            "texture_04": texture_04_image,
            "texture_05": texture_05_image,
            "texture_07": texture_07_image,
            "texture_08": texture_08_image
        }

    for (i,image_filename) in enumerate(part_list):
        part_name = image_filename[:image_filename.rfind("_")]

        breast_flag, breast_type = judge_flag_dict['breast'], judge_type_dict['breast']
        image = Image.open(os.path.join(part_dir, image_filename))
        if breast_flag and image_filename.startswith("turtleneck_shirt"):
            breast_name = breast_type + " breast"
            breast_image_filename = model_dict["atts_map"]["breast type"][breast_name][0]
            breast_image = Image.open(os.path.join(part_dir, breast_image_filename))
            image = merge_breast_image(image, breast_image)
        
        alpha = image.split()[3]

        mask = Image.new('L', image.size, 0)
        mask.paste(alpha)

        threshold = 128
        mask = mask.point(lambda p: 255 if p > threshold else 0)
        
        save_path = os.path.join(model_dict["part_path"], part_name+'_mask.png')
        if "_thigh" in part_name:
            mask = mask.rotate(-90, expand=True)
        mask.save(save_path)

        x = model_dict["photo"][part_name]["x"]
        y = model_dict["photo"][part_name]["y"]
        w = model_dict["photo"][part_name]["w"]
        h = model_dict["photo"][part_name]["h"]

        x_t = model_dict["texture"][part_name]["x"]
        y_t = model_dict["texture"][part_name]["y"]
        w_t = model_dict["texture"][part_name]["w"]
        h_t = model_dict["texture"][part_name]["h"]

        crop_region = gen_image_origin_size.crop((x, y, x + w, y + h))
        if "_thigh" in part_name:
            crop_region_rotate = crop_region.rotate(-90, expand=True)
            part = Image.new('RGBA', (w_t, h_t), (0,0,0,0))
            part.paste(crop_region_rotate, (0, 0), mask)
            # crop_region.save(os.path.join(save_time_dir, part_name+"_crop_region_rotated.png"))
        else:
            part = Image.new('RGBA', (w, h), (0,0,0,0))
            part.paste(crop_region, (0, 0), mask)

        if breast_flag and image_filename.startswith("turtleneck_shirt"):
            texture_name = map_to_texture["turtleneck_breast_shirt"]
        else:
            texture_name = map_to_texture[part_name]
        target_texture = texture_dict[texture_name]
        used_texture_list.append(texture_name)

        # repair sleeve defects
        if image_filename.startswith("left_long_sleeve"):
            if breast_flag:
                if breast_type == "big":
                    sleeve_boundary_mask_path = os.path.join(model_dict["defects_folder"],'left_long_sleeve_0_breast_0_mask.png')
                else:
                    sleeve_boundary_mask_path = os.path.join(model_dict["defects_folder"],'left_long_sleeve_0_breast_1_mask.png')
            else:
                sleeve_boundary_mask_path = os.path.join(model_dict["defects_folder"],'left_long_sleeve_0_breast_1_mask.png')
            
            sleeve_boundary_mask = Image.open(sleeve_boundary_mask_path).convert("L")
            part = repair_sleeve_defects(part, sleeve_boundary_mask, offset=18)

        if image_filename.startswith("right_long_sleeve"):
            if breast_flag:
                if breast_type == "big":
                    sleeve_boundary_mask_path = os.path.join(model_dict["defects_folder"],'right_long_sleeve_0_breast_0_mask.png')
                else:
                    sleeve_boundary_mask_path = os.path.join(model_dict["defects_folder"],'right_long_sleeve_0_breast_1_mask.png')
            else:
                sleeve_boundary_mask_path = os.path.join(model_dict["defects_folder"],'right_long_sleeve_0_breast_1_mask.png')

            sleeve_boundary_mask = Image.open(sleeve_boundary_mask_path).convert("L")
            part = repair_sleeve_defects(part, sleeve_boundary_mask, offset=18)

        if "_thigh" in part_name:
            target_area = Image.new('RGBA', (w_t,h_t), (0,0,0,0))
        else:
            target_area = Image.new('RGBA', (w,h), (0,0,0,0))
        target_texture.paste(target_area, (x_t, y_t))

        target_texture.paste(part, (x_t, y_t))
        # target_texture.save(os.path.join(save_time_dir, texture_name+"_"+str(i)+".png"))

        texture_dict[texture_name] = target_texture

    save_dir = os.path.join(save_time_dir, 'texture')
    os.makedirs(save_dir, exist_ok=True)

    for texture_name in used_texture_list:
        texture_dict[texture_name].save(os.path.join(save_dir, texture_name+'.png'))
        target_texture_list.append(texture_dict[texture_name])


def apply_eye_color(eye_color, model_dict, save_time_dir):
    if len(eye_color) > 0:
        side_list = ["left", "right"]
        texture_name = model_dict["eye"][side_list[0]]["name"]
        if os.path.exists(os.path.join(save_time_dir,"texture",texture_name+".png")):
            texture_image_path = os.path.join(save_time_dir,"texture",texture_name+".png")
        else:
            texture_image_path = os.path.join(model_dict["texture_folder"],texture_name+".png")
        texture_image = Image.open(texture_image_path).convert("RGBA")
        for side in side_list:
            x = model_dict["eye"][side]["x"]
            y = model_dict["eye"][side]["y"]
            w = model_dict["eye"][side]["w"]
            h = model_dict["eye"][side]["h"]
            # logger.info(f'x,y,w,h:{x},{y},{w},{h}')
            eye_template = os.path.join(model_dict["eye_dir"], side+"_"+eye_color+"_eye.png")

            if os.path.exists(eye_template):
                eye_image = Image.open(eye_template).convert("RGBA")
                eye_temp_w, eye_temp_h = eye_image.size
                # logger.info(f'eye_temp_w,eye_temp_h:{eye_temp_w},{eye_temp_h}')
                texture_image.paste(eye_image, (x, y))
                # logger.info('pasted')
            else:
                logger.warning('eye template not found')
        
        save_path = os.path.join(save_time_dir, "texture", texture_name+'.png')
        texture_image.save(save_path)


if __name__ == "__main__":
    # read base model configuration
    model_json_path = 'assets/model_configuration.json'
    with open(model_json_path, 'r') as f:
        model_dict = json.load(f)

    part_list = ["long_back_hair_2.png", "left_middle_hair_0.png", "right_middle_hair_0.png", "bang_hair_0.png", 
                 "left_long_sleeve_1.png", "right_long_sleeve_1.png", "turtleneck_shirt_4.png", 
                 "skirt_3.png", "left_boot_2.png", "right_boot_2.png"]

    # test eye color
    eye_color = 'black'
    save_time_dir = 'outputs/20241204/20241204-095451'
    apply_eye_color(eye_color, model_dict, save_time_dir)