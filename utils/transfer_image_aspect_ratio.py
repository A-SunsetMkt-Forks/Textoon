import cv2
import numpy as np
from PIL import Image


def convert_to_pil(image):
    if isinstance(image, Image.Image):
        return image
    elif isinstance(image, np.ndarray):
        return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    else:
        raise TypeError("Unsupported image type. Provide a PIL Image or a NumPy ndarray.")

def transfer_image_aspect_ratio_1half(image_pil):
    """
    将图片宽高比转换为1:1.5比例
    输入分辨率2951x5444
    输出分辨率3360x5040
    """
    image = convert_to_pil(image_pil)
    cropped_image = image.crop((0, 404, 2951, 5444))
    new_image = Image.new('RGB', (3360, 5040), (0, 0, 0))
    new_image.paste(cropped_image, (205, 0))
    return new_image

def restore_image_aspect_ratio(image_pil):
    """
    将图片宽高比1:1.5转换为原始分辨率2951x5444
    输入分辨率3360x5040
    输出分辨率2951x5444
    """
    image = convert_to_pil(image_pil)
    cropped_image = image.crop((205, 0, 205+2951, 5040))
    new_image = Image.new('RGB', (2951, 5444), (0, 0, 0))
    new_image.paste(cropped_image, (0, 404))
    return new_image


if __name__ == "__main__":
    image_path = 'assets/examples/combination_black.png'
    image_pil = Image.open(image_path)
    new_image = transfer_image_aspect_ratio_1half(image_pil)
    new_image.save('res.png')

    image_pil = Image.open('res.png')
    new_image = restore_image_aspect_ratio(image_pil)
    new_image.save('res2.png')