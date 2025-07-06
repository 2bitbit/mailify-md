import base64
import re
from pathlib import Path


def inline_katex_assets():
    """
    读取 katex.min.css 文件, 查找其中所有对字体文件 url() 的引用, 将这些引用替换为 Base64 编码的 Data URI,
    最终将结果保存到一个新文件 katex.inlined.css 中.
    """
    rsc_path = Path(__file__).parent.parent / "src" / "rsc"
    css_content = (rsc_path / "katex.min.css").read_text(encoding="utf-8")
    fonts_path = rsc_path / "fonts"
    output_path = rsc_path / "katex.inlined.css"

    # re.sub 会为每个匹配项调用此函数
    def replacer(match):
        font_filename = match.group(1)  # match.group(0) 是整个匹配的字符串, e.g., "url(fonts/KaTeX_Main-Regular.woff2)"
        # match.group(1) 是第一个捕获组, e.g., "KaTeX_Main-Regular.woff2"
        base64_data = base64.b64encode((fonts_path / font_filename).read_bytes()).decode("utf-8")

        # 构建新的 Data URI 格式的 url
        new_url = f'url("data:{"font/woff2"};base64,{base64_data}")'  # KaTeX 使用的字体格式是 woff2
        return new_url

    # --- 4. 执行查找和替换 ---
    # 定义正则表达式来查找 url(fonts/KaTeX_....woff2)
    # 括号 (...) 创建了一个捕获组，用于提取文件名
    pattern = re.compile(r"url\(fonts/([a-zA-Z0-9_-]+\.woff2)\)")

    # 使用 replacer 函数替换所有匹配项
    inlined_content = pattern.sub(replacer, css_content)

    # --- 5. 写入最终结果 ---
    output_path.write_text(inlined_content, encoding="utf-8")
    print(f"\n成功创建内联CSS文件: {output_path}")


# 当这个脚本作为主程序直接运行时，调用 inline_katex_assets 函数
if __name__ == "__main__":
    inline_katex_assets()
