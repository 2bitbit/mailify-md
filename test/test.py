import os, logging, asyncio, sys

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT_PATH, "src"))
from CONSTANTS import IS_TEST, CODE_STYLES, CODE_STYLE


def init():
    def set_is_test():
        global IS_TEST
        IS_TEST = True

    set_is_test()

    def logging_debug_decorator(func):
        from time import perf_counter

        last_time = perf_counter()
        now = None

        def wrapper(message, command=None):
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

    logging.debug = logging_debug_decorator(logging.debug)

    def set_logging_level():
        logging.basicConfig(level=logging.DEBUG, format="DEBUG:md_mailify: | {msg}", style="{")
        logging.getLogger("premailer").setLevel(logging.WARNING)
        logging.getLogger("playwright").setLevel(logging.WARNING)
        logging.getLogger("markdown_it").setLevel(logging.WARNING)
        logging.getLogger("pygments").setLevel(logging.WARNING)
        logging.getLogger("bs4").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    set_logging_level()


def main():
    # 导入mailify_md.py
    from mailify_md import mailify

    # 对test.md进行处理，生成test.html
    md_file_path = os.path.join(ROOT_PATH, "test", "test.md")
    html_file_path = os.path.join(ROOT_PATH, "test", "test.html")
    asyncio.run(mailify(md_file_path, html_file_path))


def auto_send_email():
    pass


if __name__ == "__main__":
    init()
    CODE_STYLE = None
    main()
