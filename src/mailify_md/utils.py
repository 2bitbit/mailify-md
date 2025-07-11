import logging
from typing import Optional
import re


# region: 工具函数
def contains_web_links(md_text: str) -> bool:
    """
    检查Markdown文本是否包含Web链接
    """
    # 移除Markdown格式的图片 `![alt](url)`
    text_without_md_images = re.sub(r"!\[.*?\]\(.*?\)", "", md_text.strip())
    # 移除HTML格式的图片 `<img ...>`
    text_without_any_images = re.sub(r"<img[^>]*>", "", text_without_md_images, flags=re.IGNORECASE)
    return bool(re.search(r"https?://", text_without_any_images))


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
