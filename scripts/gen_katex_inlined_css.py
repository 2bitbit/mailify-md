import base64, re
from pathlib import Path

rscdir = Path(__file__).parent.parent / "rsc"
srcdir = Path(__file__).parent.parent / "src"


def inline_katex_assets():
    """
    读取 katex.min.css 文件, 查找其中所有对字体文件 url() 的引用, 将这些引用替换为 Base64 编码的 Data URI,
    最终将结果保存到一个新文件 katex.inlined.css 中.
    """
    katex_min_fpath = rscdir / "katex.min.css"
    katex_inlined_fpath = srcdir / "mailify_md" / "data" / "builtins" / "katex.inlined.css"
    css_content = Path(katex_min_fpath).read_text(encoding="utf-8")

    # re.sub 会为每个匹配项调用此函数
    def replacer(match: re.Match[str]) -> str:
        font_filename = match.group(1)
        font_path = rscdir / "fonts" / font_filename
        base64_str = base64.b64encode(font_path.read_bytes()).decode("utf-8")
        return f'url("data:font/woff2;base64,{base64_str}")'

    # 定义正则表达式来查找 url(fonts/KaTeX_....woff2)并替换所有匹配项
    pattern = re.compile(r"url\(fonts/([a-zA-Z0-9_-]+\.woff2)\)")
    inlined_content = pattern.sub(replacer, css_content)

    Path(katex_inlined_fpath).write_text(inlined_content, encoding="utf-8")


# 当这个脚本作为主程序直接运行时，调用 inline_katex_assets 函数
if __name__ == "__main__":
    inline_katex_assets()
