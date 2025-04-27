import os
import json
import time
import random
import logging
from modules.prompt_to_attribute import PromptAttributeExtractor2_5
from modules.chn2eng_translation_aliyun import Chn2EngTranslation
from modules.run_comfyui_translation import call_comfyui_translate_toeng, call_comfyui_translate_tochn

logger = logging.getLogger(__name__)

def text_addition(text_prompt):
    if "独奏" not in text_prompt:
        text_prompt = "独奏, " + text_prompt
    if "1boy" not in text_prompt:
        text_prompt = "1boy, " + text_prompt
    # text_prompt = text_prompt + "，过渡自然，影视动漫，4K，超高清"
    # if "动漫风格" not in text_prompt:
    #     text_prompt = text_prompt + ", 动漫风格"
    # if "光照均匀" not in text_prompt:
    #     text_prompt = text_prompt + ", 光照均匀"
    return text_prompt

def translate_punctuation(chinese_text):
    # Map Chinese punctuation to English punctuation
    punctuation_map = {
        '，': ',',
        '。': '.',
        '：': ':',
        '；': ';',
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '「': '"',
        '」': '"',
        '？': '?',
        '！': '!',
        '‘': '\'',
        '’': '\'',
        '“': '"',
        '”': '"',
        '、': ',',
        '——': '-'
    }
    translated_text = ''.join(punctuation_map.get(char, char) for char in chinese_text)
    return translated_text

def judge_ponytail(atts_extracted):
    # Determine whether it is a ponytail hairstyle
    ponytail_flag = False
    ponytail_type = "half"
    atts_extracted_keylist = list(atts_extracted.keys())
    if "hair length" in atts_extracted_keylist:
        if atts_extracted["hair length"] == 'double ponytail':
            ponytail_flag = True
            ponytail_type = "double"
        elif atts_extracted["hair length"] == 'half up ponytail':
            ponytail_flag = True
            ponytail_type = "half"
    return ponytail_flag, ponytail_type

def judge_breast(atts_extracted):
    # Determine whether it is big breasts
    breast_flag = False
    breast_type = "standard"

    atts_extracted_keylist = list(atts_extracted.keys())
    if "breast type" in atts_extracted_keylist:
        if atts_extracted["breast type"] == 'big breast':
            breast_flag = True
            breast_type = "big"
        else:
            breast_flag = True
            breast_type = "standard"
    return breast_flag, breast_type

def eye_color_setting(atts_extracted, model_config_dict):
    # Set eye color
    atts_extracted_keylist = list(atts_extracted.keys())
    if "eye color" in atts_extracted_keylist:
        eye_color = atts_extracted["eye color"]
        if eye_color in model_config_dict["eyecolor"]:
            return eye_color
        else:
            with open(model_config_dict["text_mapping_json_path"], 'r') as f:
                post_dict = json.load(f)
            for mapping_desc in post_dict["eye color"]:
                if eye_color == mapping_desc["src"]:
                    return mapping_desc["dst"]
            eye_color = random.choice(model_config_dict["selected_eyecolor"])
            return eye_color
    else:
        eye_color = random.choice(model_config_dict["selected_eyecolor"])
        return eye_color

def atts_to_partlist_eyecolor(atts_extracted, model_config_dict):
    part_list = []
    atts_extracted_keylist = list(atts_extracted.keys())

    model_gender_dict = model_config_dict["haimeng"]
    judge_flag_dict = dict()
    judge_type_dict = dict()
    ponytail_flag, ponytail_type = judge_ponytail(atts_extracted)
    judge_flag_dict["ponytail"] = ponytail_flag
    judge_type_dict["ponytail"] = ponytail_type
    breast_flag, breast_type = judge_breast(atts_extracted)

    judge_flag_dict["breast"] = breast_flag
    judge_type_dict["breast"] = breast_type
    print(f'judege_flag_dict: {judge_flag_dict}, judge_type_dict: {judge_type_dict}')

    for key, value in model_gender_dict["atts_map"].items():
        if key == "hair length":
            if ponytail_flag:
                if ponytail_type == "double":
                    # selected = model_dict["atts_map"]["hair length"]["double-ponytail"]
                    selected = model_gender_dict["atts_map"]["hair length"]["double ponytail"]
                else:
                    # selected = model_dict["atts_map"]["hair length"]["half-ponytail"]
                    selected = model_gender_dict["atts_map"]["hair length"]["half up ponytail"]
            else:
                if key in atts_extracted_keylist:
                    modeldict_partkey_list = ["long","middle","short"]
                    if atts_extracted[key] in modeldict_partkey_list:
                        selected = model_gender_dict["atts_map"][key][atts_extracted[key]]
                    else:
                        key_choice = random.choice(modeldict_partkey_list)
                        logger.info(f"parsing class not in atts list, random choose {key_choice}")
                        selected = model_gender_dict["atts_map"][key][key_choice]
                else:
                    class_list = ["long","middle","short"]
                    random_class = random.choice(class_list)
                    selected = model_gender_dict["atts_map"][key][random_class]
        elif key == "bang type":
            if ponytail_flag:
                selected = model_gender_dict["atts_map"]["bang type"]["ponytail"]
            else:
                if key in atts_extracted_keylist:
                    modeldict_partkey_list = ["long","middle","short"]
                    if atts_extracted[key] in modeldict_partkey_list:
                        selected = model_gender_dict["atts_map"][key][atts_extracted[key]]
                    else:
                        key_choice = random.choice(modeldict_partkey_list)
                        logger.info(f"parsing class not in atts list, random choose {key_choice}")
                        selected = model_gender_dict["atts_map"][key][key_choice]
                else:
                    class_list = ["long","middle","short"]
                    random_class = random.choice(class_list)
                    selected = model_gender_dict["atts_map"][key][random_class]
        elif key == "breast type":
            selected = ""
        elif key not in ["skirt type", "pants type"]:
            if key in atts_extracted_keylist:
                modeldict_partkey_list = list(model_gender_dict["atts_map"][key].keys())
                if atts_extracted[key] in modeldict_partkey_list:
                    selected = model_gender_dict["atts_map"][key][atts_extracted[key]]
                else:
                    key_choice = random.choice(modeldict_partkey_list)
                    logger.info(f"parsing class not in atts list, random choose {key_choice}")
                    selected = model_gender_dict["atts_map"][key][key_choice]
            else:
                class_list = list(model_gender_dict["atts_map"][key].keys())
                random_class = random.choice(class_list)
                selected = model_gender_dict["atts_map"][key][random_class]
        else:
            selected = ""

        if isinstance(selected, list):
            part_list.extend(selected)
        elif isinstance(selected, dict):
            random_selected = random.choice(list(selected.values()))
            part_list.extend(random_selected)
        else:
            continue
    # Lower body clothing selection
    if "skirt type" in atts_extracted_keylist and "pants type" in atts_extracted_keylist:
        part_name = random.choice(["skirt type", "pants type"])
        selected = model_gender_dict["atts_map"][part_name][atts_extracted[part_name]]
    elif "skirt type" not in atts_extracted_keylist and "pants type" not in atts_extracted_keylist:
        part_name = random.choice(["skirt type", "pants type"])
        class_list = list(model_gender_dict["atts_map"][part_name].keys())
        random_class = random.choice(class_list)
        selected = selected = model_gender_dict["atts_map"][part_name][random_class]
    else:
        if "skirt type" in atts_extracted_keylist:
            part_name = "skirt type"
            selected = model_gender_dict["atts_map"][part_name][atts_extracted[part_name]]
        else:
            part_name = "pants type"
            selected = model_gender_dict["atts_map"][part_name][atts_extracted[part_name]]
    if isinstance(selected, list):
        part_list.extend(selected)
    elif isinstance(selected, dict):
        random_selected = random.choice(list(selected.values()))
        part_list.extend(random_selected)
    else:
        ValueError("Error: skirt or pant error!")

    # Set eye color
    eye_color = eye_color_setting(atts_extracted, model_config_dict)
    return part_list, eye_color, judge_flag_dict, judge_type_dict

def parsing_prompt_to_partlist(text_prompt, model_config_dict, translation_services):
    """
    Parse the widget attribute eye color from the input prompt
    """
    start_time = time.time()
    text_model_dir = model_config_dict["text_model_dir"]
    attr_extractor = PromptAttributeExtractor2_5(model_dir=text_model_dir)
    # translate chn to eng
    if translation_services == "aliyun":
        # aliyun Translate_AK
        chn2eng = Chn2EngTranslation()
        chinese_prompt = chn2eng.translate_chn(text_prompt)
    elif translation_services == "google":
        # google
        chinese_prompt = call_comfyui_translate_tochn(text_prompt)
    else:
        raise ValueError("Error: translation_services error!")
    atts_extracted = attr_extractor.extract_attribute(chinese_prompt)
    end_time = time.time()
    logger.info(f"attr parsing Time cost: {end_time - start_time}")
    
    part_list, eye_color, judge_flag_dict, judge_type_dict = atts_to_partlist_eyecolor(atts_extracted, model_config_dict)
    logger.info(f'\npart_list: {part_list}\neye_color: {eye_color}\njudge_flag_dict: {judge_flag_dict}\njudge_type_dict: {judge_type_dict}\n')

    text_prompt_add = text_addition(text_prompt)
    # translate chn to eng
    if translation_services == "aliyun":
        # aliyun Translate_AK
        chn2eng = Chn2EngTranslation()
        english_prompt_origin = chn2eng.translate_eng(text_prompt_add)
    elif translation_services == "google":
        # google
        english_prompt_origin = call_comfyui_translate_toeng(text_prompt_add)
    else:
        raise ValueError("Error: translation_services error!")
    
    english_prompt = translate_punctuation(english_prompt_origin)
    logger.info(f'\nenglish_prompt: {english_prompt}, \ntext_prompt: {text_prompt_add}, \nchinese_prompt: {chinese_prompt}, \nAttribute: {atts_extracted}')
    return english_prompt, part_list, eye_color, judge_flag_dict, judge_type_dict