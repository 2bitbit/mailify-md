# -*- coding: utf-8 -*-

import asyncio
import base64
from typing import List, Dict
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from playwright.async_api import async_playwright, Page
from premailer import Premailer


class MarkdownEmailConverter:
    """
    一个将Markdown转换为邮件优化HTML的框架。

    工作流程:
    1. 使用 markdown-it-py 和 Pygments 将Markdown解析为带有高亮代码的HTML。
    2. 使用 Playwright 启动无头浏览器，加载包含KaTeX JS库的HTML模板。
    3. 浏览器执行JavaScript，将LaTeX公式渲染为HTML和CSS。
    4. Playwright对每个渲染后的公式进行截图，并编码为Base64。
    5. 使用 BeautifulSoup 将复杂的KaTeX HTML结构替换为简单的、带有Base64数据的<img>标签。
    6. 使用 Premailer 将所有<style>规则内联到HTML元素中，并进行最终清理。
    """

    def __init__(self, template_html: str):
        """
        初始化转换器。
        :param template_html: 包含占位符 '<!--主题内容输入到这里-->' 的HTML模板。
        """
        if "<!--主题内容输入到这里-->" not in template_html:
            raise ValueError("HTML模板中必须包含 '<!--主题内容输入到这里-->' 占位符。")
        self.template = template_html
        self.md = self._setup_markdown_parser()

    def _setup_markdown_parser(self) -> MarkdownIt:
        """配置markdown-it-py解析器，并集成Pygments进行代码高亮。"""

        def pygments_highlighter(code: str, lang: str, attrs: str) -> str:
            if not lang:
                return f"<pre><code>{code}</code></pre>"
            try:
                lexer = get_lexer_by_name(lang, stripall=True)
                formatter = HtmlFormatter(style="github-dark", noclasses=True, nowrap=True)
                return highlight(code, lexer, formatter)
            except:
                return f"<pre><code class-name='language-{lang}'>{code}</code></pre>"

        md_options = {"highlight": pygments_highlighter, "linkify": False}
        return MarkdownIt("gfm-like", md_options).use(front_matter_plugin)

    async def _embed_katex_as_base64(self, page: Page) -> str:
        """在Playwright页面中查找KaTeX元素，截图并替换为Base64内嵌的img标签。"""
        katex_elements = await page.query_selector_all(".katex")
        if not katex_elements:
            print("未找到KaTeX公式，跳过截图步骤。")
            return await page.content()

        print(f"找到 {len(katex_elements)} 个KaTeX数学公式，正在进行截图和Base64内嵌...")

        page_content = await page.content()
        soup = BeautifulSoup(page_content, "html.parser")

        bs_elements = soup.find_all(class_="katex")

        if len(katex_elements) != len(bs_elements):
            print("警告：Playwright和BeautifulSoup找到的KaTeX元素数量不匹配，可能导致替换错误。")
            return page_content

        for i, element_handle in enumerate(katex_elements):
            bs_element = bs_elements[i]
            try:
                # 从KaTeX渲染结果中提取原始LaTeX源代码，用于alt属性
                latex_source_tag = bs_element.find("annotation", encoding="application/x-tex")
                latex_source = latex_source_tag.string if latex_source_tag else ""

                screenshot_bytes = await element_handle.screenshot(type="png")
                base64_data = "data:image/png;base64," + base64.b64encode(screenshot_bytes).decode()

                # 创建带有alt属性的img标签，用于复制
                img_tag = soup.new_tag(
                    "img", src=base64_data, alt=latex_source.strip(), style="vertical-align: middle; max-width: 100%;"
                )
                bs_element.replace_with(img_tag)
                print(f"  - 公式 {i+1} 已成功转换为Base64图片，alt属性已设置。")
            except Exception as e:
                print(f"处理第 {i+1} 个KaTeX公式时出错: {e}")

        return str(soup)

    def _final_cleanup_and_inline(self, html_content: str) -> str:
        """使用Premailer进行CSS内联，并移除不必要的脚本和链接标签。"""
        print("正在使用 Premailer 内联CSS样式并进行最终清理...")

        soup = BeautifulSoup(html_content, "html.parser")
        for script_tag in soup.find_all("script"):
            script_tag.decompose()

        premailer = Premailer(str(soup), remove_classes=False, keep_style_tags=False, cssutils_logging_level="CRITICAL")
        return premailer.transform()

    async def convert(self, markdown_text: str) -> str:
        """
        执行从Markdown到邮件优化HTML的完整转换流程。
        """
        print("步骤 1/5: 正在将Markdown转换为HTML...")
        md_content = self.md.render(markdown_text)

        full_html_to_render = self.template.replace("<!--主题内容输入到这里-->", md_content)

        async with async_playwright() as p:
            print("步骤 2/5: 正在启动无头浏览器...")
            browser = await p.chromium.launch()
            page = await browser.new_page()

            print("步骤 3/5: 正在加载HTML并等待JavaScript渲染 (KaTeX)...")
            await page.set_content(full_html_to_render, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            print("步骤 4/5: 正在处理KaTeX公式（截图并内嵌）...")
            processed_html = await self._embed_katex_as_base64(page)

            await browser.close()
            print("浏览器已关闭。")

        # 步骤 5/5: 执行CSS内联和最终清理
        final_html = self._final_cleanup_and_inline(processed_html)

        print("\n转换流程全部完成！")
        return final_html


# ==============================================================================
# 使用示例
# ==============================================================================
async def main():
    """主函数，用于演示转换器的使用。"""

    # 您的HTML模板
    # 修正：模板中的CSS已更新为"邮件安全"模式，移除了CSS变量
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
        <title>邮件标题</title>
        <style>
            /* Custom Dark Mode Theme with User Styles */
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                line-height: 1.6;
                color: #FFFFFF; /* White text */
                background-color: #0d1117; /* Dark background */
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 680px;
                margin: 20px auto;
                padding: 20px 40px;
                border: 5px solid #00a549; /* Restored user's custom green border */
                border-radius: 20px; /* Restored user's custom border radius */
                background-color: #161b22; /* Dark container background */
                color: #FFFFFF; /* Ensure all text inside container is white */
            }
            :not(pre)>code {
                color: #58a6ff; /* Inline code text color */
                font-family: 'Source Code Pro', monospace;
                font-size: 85%;
                background-color: rgba(110,118,129,0.4); /* Inline code background */
                border-radius: 6px;
                font-weight: bolder;
                padding: .1em .3em;
            }
            pre {
                /* Pygments with noclasses=True will add its own inline style. This is a fallback. */
                font-size: 0.95em;
                border-radius: 10px;
                padding: 1em;
                overflow-x: auto;
                background-color: #0d1117;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #FFFFFF; /* White headings */
            }
            h1 {
                border-bottom: 3px solid #FF6D2D; /* Restored user's custom orange border */
                padding-bottom: 10px;
            }
            a {
                color: #58a6ff;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <!--主题内容输入到这里-->
        </div>
        <div class="scripts" style="display:none;">
            <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
            <script>
                document.addEventListener("DOMContentLoaded", function () {
                    renderMathInElement(document.body, {
                        delimiters: [
                            { left: '$$', right: '$$', display: true },
                            { left: '$', right: '$', display: false }
                        ]
                    });
                });
            </script>
        </div>
    </body>
    </html>
    """

    markdown_source = """
# 一份包含代码和公式的报告

这是一个演示，展示了如何将Markdown、代码和数学公式转换为一封精美的HTML邮件。

## 代码高亮

下面是一个Python代码示例，它会被 `Pygments` 自动高亮。

```python
def greet(name: str):
    # 这只是一个简单的问候函数
    print(f"Hello, {name}! Welcome to the world of advanced email generation.")

greet("Developer")
```

## 数学公式渲染

我们将使用KaTeX来渲染LaTeX公式。

行内公式，例如爱因斯坦的质能方程 $E=mc^2$，应该能无缝地融入文本中。

块级公式则会居中显示，例如著名的高斯积分：

$$
\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}
$$

感谢您的阅读！
"""

    converter = MarkdownEmailConverter(template_html=html_template)
    final_html_output = await converter.convert(markdown_source)

    output_filename = "output_email.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_html_output)

    print(f"\n成功！最终的HTML文件已保存为 {output_filename}")
    print("您现在可以用浏览器打开这个文件来预览最终效果。")


if __name__ == "__main__":
    asyncio.run(main())
