import logging
from typing import Optional, Tuple
from PIL import Image
import io

# region: 图像处理
def trim_image_by_color(image_bytes: bytes, bg_color: tuple) -> Tuple[bytes, int]:
    """
    通过将像素与指定的RGB背景色进行对比，来精确裁剪图像的空白。
    return: 新的图像字节, 裁切后的物理像素宽度。
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixels = img.load()

    width, height = img.size
    left, top, right, bottom = width, height, -1, -1

    # 遍历所有像素，求出公式内容所在的大致矩形
    for y in range(0, height, 2):  # 只是差 2 个像素，速度却快了2倍
        for x in range(0, width, 2):
            if pixels[x, y] != bg_color:
                left, top, right, bottom = min(left, x), min(top, y), max(right, x), max(bottom, y)

    # 略微扩展边界框，并确保坐标在图像范围内
    left, top, right, bottom = max(0, left - 2), max(0, top - 2), min(width - 1, right + 2), min(height - 1, bottom + 2)

    trimmed_image = img.crop((left, top, right + 1, bottom + 1))  # 裁切图像 (crop的右下角坐标是开区间)
    
    buffer = io.BytesIO()
    trimmed_image.save(buffer, format="PNG")
    return buffer.getvalue(), trimmed_image.size[0]
# endregion

# region: 日志
def logging_debug_decorator(func):
    from time import perf_counter

    last_time = perf_counter()
    now = None

    def wrapper(message: str, command: Optional[int] = None) -> None:
        """
        None: 普通地打日志
        0: 重新开始计时
        1: 打印与上次计时的间隔
        """
        nonlocal last_time, now
        if command is None:
            return func(f"                        | {message}")
        elif command == 0:
            last_time = perf_counter()
            return func(f"开始计时:        0.00s  | {message}")
        else:
            now = perf_counter()
            delta = now - last_time
            last_time = now
            return func(f"与上次计时间隔: {delta:5.2f}s  | {message}")

    return wrapper


log = logging_debug_decorator(logging.debug)
# endregion
