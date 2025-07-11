# mailify_md/cli.py
import typer
from typing import Annotated, Optional
from pathlib import Path
from .mailify_md import MailifyMD

app = typer.Typer()


@app.command()
def main(
    input_fpath: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            writable=True,
            help="待修改的.md文件路径",
        ),
    ],
    output_path: Annotated[
        Optional[Path],
        typer.Argument(
            writable=True,
            help="输出的.html文件路径。如果未提供，将默认在输入文件同目录下生成同名 .html 文件。",
        ),
    ] = None,
    theme: Annotated[
        str,
        typer.Option(
            "-t",
            "--theme",
            help="要使用的主题样式, 支持light, dark, 自定义css文件路径",
        ),
    ] = "dark",
):
    """
    将markdown文件转换为专门为邮件环境设计的html文件。支持自定义主题样式css。
    """
    import asyncio

    if not input_fpath.is_absolute():
        input_fpath = input_fpath.resolve()

    if output_path is None:
        output_path = input_fpath.with_suffix(".html")
    if input_fpath.suffix not in (".md", ".markdown"):
        raise ValueError(f"请检查输入参数是否为正确的Markdown文件: {input_fpath}")
    if output_path.suffix not in (".html", ".htm", ""):
        raise ValueError(f"请检查输出参数是否为正确的HTML文件: {output_path}")

    mailify_md = MailifyMD(str(input_fpath), str(output_path), theme)
    asyncio.run(mailify_md.run())


# 用于 pyproject.toml 入口点的包装函数
def main_entry():
    app()
