import io
import cv2
import base64
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)

def pil_to_cv2(image):
    if isinstance(image, Image.Image):
        img_np = np.array(image)
        img_cv2 = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        return img_cv2
    else:
        return image

def cv2_to_pil(image_cv2):
    if isinstance(image_cv2, np.ndarray):
        img_pil = Image.fromarray(cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB))
        return img_pil
    else:
        return image_cv2

def alpha_to_rgb(image_pil):
    if image_pil.mode == 'RGBA':
        black_background = Image.new("RGB", image_pil.size, (0, 0, 0))
        black_background.paste(image_pil, mask=image_pil.split()[3])
        return black_background
    else:
        return image_pil

def pil_to_mask(image_pil):
    image_cv2 = pil_to_cv2(image_pil)
    gray_image = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)

    _, mask = cv2.threshold(gray_image, 1, 255, cv2.THRESH_BINARY)
    
    return mask

def alphapil_to_mask(image_pil):
    image_pil_rgb = alpha_to_rgb(image_pil)
    image_gray_mask = pil_to_mask(image_pil_rgb)

    return image_gray_mask

def judge_trouser_or_skirt(combination_image_cv2):
    if combination_image_cv2.shape[2] == 4:
        b, g, r, a = cv2.split(combination_image_cv2)
        bgr_image = cv2.merge((b, g, r))
    else:
        bgr_image = combination_image_cv2

    gray_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)

    x, y = 1350, 2525
    if x < gray_image.shape[1] and y < gray_image.shape[0]:
        pixel_value = gray_image[y, x]
    else:
        logger.info(f"Coordinates (x={x}, y={y}) are out of the image bounds.")

    return pixel_value


def pil_to_base64(image_pil):
    buffered = io.BytesIO()
    image_pil.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()
    image_base64_str = base64.b64encode(image_bytes).decode('utf-8')

    return image_base64_str

def cv2_to_base64(image_cv2):
    success, buffer = cv2.imencode('.png', image_cv2)
    if not success:
        raise RuntimeError("Could not encode image to memory.")
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return image_base64