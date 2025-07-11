import logging, subprocess
from pathlib import Path

TEST_PATH = Path(__file__).parent


def init():
    def check_and_install():
        """
        通过比较 pyproject.toml 的修改时间与 .egg-info 目录的修改时间，
        检查是否需要重新安装依赖。
        """
        pyproject_toml_file = TEST_PATH.parent / "pyproject.toml"
        egg_info_dir = TEST_PATH.parent / "src" / "mailify_md.egg-info"
        if pyproject_toml_file.stat().st_mtime > egg_info_dir.stat().st_mtime:
            print("信息: pyproject.toml 文件已被修改，正在重新安装...")
            subprocess.run(["pip", "install", "-e", str(TEST_PATH.parent)], check=True)

    check_and_install()

    def set_logging_level():
        logging.basicConfig(level=logging.DEBUG, format="{levelname:<8}:{name} | {msg}", style="{")
        logging.getLogger("premailer").setLevel(logging.WARNING)
        logging.getLogger("playwright").setLevel(logging.WARNING)
        logging.getLogger("markdown_it").setLevel(logging.WARNING)
        logging.getLogger("markdown-it-py").setLevel(logging.WARNING)
        logging.getLogger("pygments").setLevel(logging.WARNING)
        logging.getLogger("bs4").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)

    set_logging_level()


def main():
    from mailify_md.cli import main

    md_file_path = Path(TEST_PATH / "test.md")
    directly_run_html_path = TEST_PATH / "directly_run" / "test_directly_run.html"
    cli_run_html_path = TEST_PATH / "cli_run" / "test_cli_run.html"
    python_run_html_path = TEST_PATH / "python_run" / "test_python_run.html"
    # theme = ??

    print("直接运行".ljust(150, "-"))
    main(md_file_path, directly_run_html_path)
    print("python 运行".ljust(150, "-"))
    subprocess.run(["python", "-m", "mailify_md", str(md_file_path), str(python_run_html_path)], check=True)
    print("cli 运行".ljust(150, "-"))
    subprocess.run(["mailify-md", str(md_file_path), str(cli_run_html_path)], check=True)

    if python_run_html_path.read_text() == cli_run_html_path.read_text() == directly_run_html_path.read_text():
        print("运行结果: html 文件内容一致。")
    else:
        raise Exception("运行结果: html 文件内容不一致。")


if __name__ == "__main__":
    init()
    main()
