import os, logging, asyncio, sys

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT_PATH, "src"))


def init():
    def set_logging_level():
        logging.basicConfig(level=logging.DEBUG, format="{levelname:<8}:md_mailify | {msg}", style="{")
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
    main()
