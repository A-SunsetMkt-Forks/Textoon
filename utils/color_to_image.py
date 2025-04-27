from PIL import Image
import os
import glob


def color2image():
    color2rgb = {
                    'red': (255, 0, 0),            # 红
                    'orange': (255, 165, 0),       # 橙
                    'yellow': (195, 205, 35),      # 黄
                    'green': (14, 255, 54),        # 绿
                    'blue': (49, 145, 255),        # 蓝
                    'purple': (128, 0, 128),       # 紫
                    'pink': (255, 192, 203),       # 粉
                    'brown': (123, 71, 11),        # 棕
                    'black': (10, 10, 10),         # 黑
                    'white': (230, 230, 230),      # 白
                    'gray': (128, 128, 128),       # 灰
                    'gold': (212, 157, 62),        # 金
    }

    # 图片大小
    image_size = (100, 100)

    for color_name, rgb in color2rgb.items():
        # 创建一个新的图像，使用RGB模式和指定的颜色
        img = Image.new('RGB', image_size, rgb)
        
        # 保存图片，文件名使用颜色名称
        img.save(f'outputs/color_images/{color_name}.png')
        print(f'Successfully created image for color: {color_name}')

def extract_eye_template():
    dst_dir = "assets/haimeng/eye"
    src_dir = "outputs/eye_template"
    template_list = sorted(glob.glob(os.path.join(src_dir, "*", "色彩迁移结果.png")))
    for src_image_path in template_list:
        image_name = src_image_path.split("/色彩迁移结果")[0].split("/")[-1] + "_eye.png"
        dst_image_path = os.path.join(dst_dir, image_name)
        print(dst_image_path)
        Image.open(src_image_path).save(dst_image_path)


if __name__ == '__main__':
    # color2image()
    extract_eye_template()