# -*- coding: utf-8 -*-
import logging
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page
import base64
from premailer import Premailer
from CONSTANTS import HTML_TEMPLATE, STYLE_HTML, IS_TEST


async def mailify(md_file_path, html_file_path):
    """
    将 Markdown 转换为邮件优化的 HTML。

    工作流程:
    1. 使用 融入了 Pygments 的 MarkdownIt，将Markdown解析为带有高亮代码的HTML，嵌入 HTML 模板中。
    2. 使用 Playwright 启动无头浏览器，将LaTeX公式渲染为HTML和CSS，并对每个渲染后的公式进行截图，并编码为Base64。
    3. 使用 BeautifulSoup 将复杂的KaTeX HTML结构替换为简单的、带有Base64数据的<img>标签。
    4. 使用 Premailer 将所有<style>规则内联到HTML元素中，并进行最终清理。
    """

    def setup_md_parser() -> MarkdownIt:
        """配置markdown-it-py解析器，并集成Pygments进行代码高亮。"""

        def pygments_highlighter(code: str, lang: str, attrs: str):
            from html import escape

            if not lang:
                # 对于没有指定语言的代码块，仅进行HTML转义。
                # MarkdownIt 会自动将其包裹在 <pre><code> 标签中。
                return escape(code)
            try:
                lexer = get_lexer_by_name(lang, stripall=True)
                # 1. `nowrap=True` 是必须的。它让 Pygments 只返回高亮后的 <span> 内容，而不会添加外层的 <div class="highlight"> 和 <pre> 标签。
                # 2. `noclasses=True` 生成内联样式，这对于邮件客户端兼容性最好。
                formatter = HtmlFormatter(
                    style=globals().get("CODE_STYLE", "default"),
                    nowrap=True,
                    noclasses=True,
                )
                # highlight的返回值现在是纯净的、可直接放入<code>标签的HTML
                return highlight(code, lexer, formatter)
            except:
                # 如果找不到指定的语言，同样只进行HTML转义。
                # MarkdownIt 依然会为其包裹 <pre><code class="language-..."> 标签。
                return escape(code)

        return MarkdownIt("gfm-like", {"highlight": pygments_highlighter, "linkify": True})

    md_parser = setup_md_parser()

    async def embed_katex_as_base64(page: Page) -> str:
        """在Playwright页面中查找KaTeX元素，截图并替换为Base64内嵌的img标签。"""
        soup = BeautifulSoup(await page.content(), "html.parser")
        katex_elements, bs_elements = await page.query_selector_all(".katex"), soup.find_all(class_="katex")
        if not katex_elements:
            logging.debug("未找到KaTeX公式，跳过截图替换公式步骤。")
            return await page.content()
        if len(katex_elements) != len(bs_elements):
            raise ValueError("Playwright和BeautifulSoup找到的KaTeX元素数量不匹配，跳过截图替换公式步骤。")

        logging.debug(f"找到 {len(katex_elements)} 个KaTeX数学公式，开始进行截图和Base64内嵌...")
        for i in range(len(katex_elements)):
            kt_element, bs_element = katex_elements[i], bs_elements[i]
            try:
                # 从KaTeX渲染结果中提取原始LaTeX源代码，用于alt属性
                latex_source_tag = bs_element.find("annotation", encoding="application/x-tex")
                latex_source = latex_source_tag.string if latex_source_tag else ""

                screenshot_bytes = await kt_element.screenshot(type="png")
                base64_data = "data:image/png;base64," + base64.b64encode(screenshot_bytes).decode()
                img_tag = soup.new_tag(
                    "img",
                    src=base64_data,
                    alt=latex_source.strip(),
                    style="vertical-align: middle; max-width: 100%;",
                )
                bs_element.replace_with(img_tag)
                logging.debug(f"  - 公式 {i+1} 已成功转换为Base64图片。")
            except Exception as e:
                logging.debug(f"处理第 {i+1} 个KaTeX公式时出错: {e}")
        logging.debug(f"KaTeX公式截图和Base64内嵌完成")
        return str(soup)

    def final_cleanup_and_inline(html_content: str) -> str:
        """内联CSS样式并移除脚本"""
        # 移除脚本
        logging.debug(f"开始移除脚本...")
        soup = BeautifulSoup(html_content, "html.parser")
        for script_tag in soup.find_all("script"):
            script_tag.decompose()

        html_without_scripts = str(soup)
        logging.debug(f"移除脚本完成")

        # 内联CSS样式
        logging.debug(f"开始内联CSS样式...")
        premailer = Premailer(
            html_without_scripts,
            remove_classes=False,
            keep_style_tags=False,
            cssutils_logging_level="CRITICAL",
        )
        logging.debug(f"内联CSS样式完成")
        return premailer.transform()

    async def convert(markdown_text: str) -> str:
        """
        执行从Markdown到邮件优化HTML的完整转换流程。
        """
        logging.debug(f"步骤 1/5: 开始将Markdown转换为HTML...", 0)
        full_html_to_render = HTML_TEMPLATE.format(content=md_parser.render(markdown_text), style=STYLE_HTML)

        async with async_playwright() as p:
            logging.debug(f"步骤 2/5: 开始启动无头浏览器预渲染...", 1)
            browser = await p.chromium.launch()
            page = await browser.new_page()

            logging.debug(f"步骤 3/5: 开始加载HTML并等待JavaScript渲染 (KaTeX)...", 1)
            await page.set_content(full_html_to_render, wait_until="networkidle")
            await page.wait_for_timeout(500)

            logging.debug(f"步骤 4/5: 开始处理KaTeX公式（截图并内嵌）...", 1)
            processed_html = await embed_katex_as_base64(page)

            await browser.close()

        logging.debug(f"步骤 5/5: 执行CSS内联和最终清理...", 1)
        final_html = final_cleanup_and_inline(processed_html)

        logging.debug(f"转换流程全部完成!", 1)
        return final_html

    with open(md_file_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    converted_html = await convert(md_text)
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(converted_html)
    print(f"转换后的HTML已保存到 {html_file_path}。")


if __name__ == "__main__" or IS_TEST:
    import sys, logging, asyncio

    try:
        asyncio.run(mailify(sys.argv[1], sys.argv[2]))
    except Exception as e:
        print(f"Error: {e}.")
