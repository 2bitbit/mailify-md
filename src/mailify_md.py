# -*- coding: utf-8 -*-
from utils import log, trim_image_by_color
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup
import sys, logging, asyncio, re, base64
from playwright.async_api import async_playwright, Page
from premailer import Premailer
from CONSTANTS import HTML_TEMPLATE, CODE_STYLE, KATEX_CSS, CUSTOM_CSS, KATEX_JS, AUTO_RENDER_JS


async def mailify(md_file_path, html_file_path):
    """
    将 Markdown 转换为邮件优化的 HTML。

    工作流程:
    1. 使用 融入了 Pygments 的 MarkdownIt, 将Markdown解析为带有高亮代码的HTML, 嵌入 HTML 模板中。
    2. 使用 Playwright 启动无头浏览器, 将LaTeX公式渲染为HTML和CSS, 并对每个渲染后的公式进行截图, 并编码为Base64。
    3. 使用 BeautifulSoup 将复杂的KaTeX HTML结构替换为简单的、带有Base64数据的<img>标签。
    4. 使用 Premailer 将所有<style>规则内联到HTML元素中, 并进行最终清理。
    """

    def setup_md_parser() -> MarkdownIt:
        """配置markdown-it-py解析器, 并集成Pygments进行代码高亮。"""

        def pygments_highlighter(code: str, lang: str, attrs: str):
            from html import escape

            if not lang:
                # 对于没有指定语言的代码块, 仅进行HTML转义。
                # MarkdownIt 会自动将其包裹在 <pre><code> 标签中。
                return escape(code)
            try:
                lexer = get_lexer_by_name(lang, stripall=True)
                # 1. `nowrap=True` 是必须的。它让 Pygments 只返回高亮后的 <span> 内容, 而不会添加外层的 <div class="highlight"><pre> 标签。
                # 2. `noclasses=True` 生成内联样式, 这对于邮件客户端兼容性最好。
                formatter = HtmlFormatter(
                    style=CODE_STYLE,
                    nowrap=True,
                    noclasses=True,
                )
                # highlight的返回值现在是纯净的、可直接放入<code>标签的HTML
                return highlight(code, lexer, formatter)
            except:
                # 如果找不到指定的语言, 同样只进行HTML转义。
                # MarkdownIt 依然会为其包裹 <pre><code class="language-..."> 标签。
                return escape(code)

        return MarkdownIt("gfm-like", {"highlight": pygments_highlighter, "linkify": True})

    async def embed_katex_as_base64(page: Page, device_scale_factor: int) -> str:
        """在Playwright页面中查找KaTeX元素, 截图并替换为Base64内嵌的img标签。"""
        soup = BeautifulSoup(await page.content(), "html.parser")

        # 1. 动态获取容器背景色, 用于后续的精确裁切
        container_element = await page.query_selector(".container")
        bg_color_rgb_str = await container_element.evaluate("el => window.getComputedStyle(el).backgroundColor")
        match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", bg_color_rgb_str)
        if match:
            bg_color_tuple = tuple(int(c) for c in match.groups())
        else:
            raise ValueError(f"无法解析背景色 {bg_color_rgb_str}")

        # 2. 找到所有公式的顶层容器(.katex-display 或 .katex), 这将用于后续的HTML替换
        container_selector = ".katex-display, :not(.katex-display) > .katex"
        katex_containers, bs_containers = await page.query_selector_all(container_selector), soup.select(container_selector)

        if not katex_containers:
            log("未找到KaTeX公式, 跳过截图替换公式步骤。")
            return await page.content()
        if len(katex_containers) != len(bs_containers):
            raise ValueError("Playwright和BeautifulSoup找到的KaTeX元素数量不匹配, 跳过截图替换公式步骤。")

        log(f"找到 {len(katex_containers)} 个KaTeX数学公式, 开始进行截图和Base64内嵌...")
        for i in range(len(katex_containers)):
            kt_container, bs_container = katex_containers[i], bs_containers[i]
            try:
                is_display_formula = await kt_container.evaluate("el => el.classList.contains('katex-display')")

                element_to_screenshot = None

                if is_display_formula:
                    # 对于块级公式, 我们截图其内部的 `.katex` 元素。
                    # 它的 'inline-block' 样式能确保截图边界紧凑。
                    element_to_screenshot = await kt_container.query_selector(".katex")
                    if element_to_screenshot:
                        # 截图前, 必须显式地将源码标签隐藏, 否则它会出现在图片中。
                        annotation_el = await element_to_screenshot.query_selector("annotation")
                        if annotation_el:
                            await annotation_el.evaluate("el => el.style.display = 'none'")
                else:
                    # 对于行内公式, 截图内部的 `.katex-html` 是最简单且有效的方法, 
                    # 它能天然地忽略旁边的源码标签。
                    element_to_screenshot = await kt_container.query_selector(".katex-html")

                if not element_to_screenshot:
                    logging.warning(f"  - 公式 {i+1} 内部未找到可截图元素, 已跳过。")
                    continue

                # 从原始的 BeautifulSoup 容器中找到源码, 用于 alt 标签
                latex_source_tag = bs_container.find("annotation", encoding="application/x-tex")
                latex_source = latex_source_tag.string if latex_source_tag else ""

                screenshot_bytes = await element_to_screenshot.screenshot(type="png")

                # 使用基于颜色对比的算法裁切截图中的空白区域
                trimmed_bytes, physical_width = trim_image_by_color(screenshot_bytes, bg_color_tuple)

                # 将物理像素宽度转换回 CSS 使用的逻辑像素宽度
                # 注意：这里的 '3' 必须与 page 创建时的 device_scale_factor 一致
                css_width = physical_width / device_scale_factor

                # 根据公式类型应用不同的样式
                if is_display_formula:
                    # 块级公式应居中显示
                    img_style = f"display: block; margin: 0.5em auto; width: {css_width}px; height: auto; max-width: 100%;"
                else:
                    # 行内公式应与文本对齐
                    img_style = f"width: {css_width}px; height: auto; vertical-align: middle; max-width: 100%;"

                base64_data = "data:image/png;base64," + base64.b64encode(trimmed_bytes).decode()
                img_tag = soup.new_tag(
                    "img",
                    src=base64_data,
                    alt=latex_source.strip(),
                    style=img_style,
                )
                # 用生成的 <img> 标签替换掉整个公式容器
                bs_container.replace_with(img_tag)
                log(f"  - 公式 {i+1} 已成功转换为Base64图片。")
            except Exception as e:
                log(f"处理第 {i+1} 个KaTeX公式时出错: {e}")
        log(f"KaTeX公式截图和Base64内嵌完成")
        return str(soup)

    def final_cleanup_and_inline(html_content: str) -> str:
        """内联CSS样式并移除脚本"""
        # 移除脚本
        log(f"开始移除脚本...")
        soup = BeautifulSoup(html_content, "html.parser")
        for script_tag in soup.find_all("script"):
            script_tag.decompose()

        html_content = str(soup)
        log(f"移除脚本完成")

        # 内联CSS样式
        log(f"开始内联CSS样式...")
        premailer = Premailer(
            html_content,
            remove_classes=False,
            keep_style_tags=False,
            cssutils_logging_level="CRITICAL",
        )
        log(f"内联CSS样式完成")
        return premailer.transform()

    async def convert(markdown_text: str) -> str:
        """
        执行从Markdown到邮件优化HTML的完整转换流程。
        """
        log(f"步骤 1/5: 开始将Markdown转换为HTML...", 0)
        full_html_to_render = HTML_TEMPLATE.format(
            katex_css=KATEX_CSS,
            custom_css=CUSTOM_CSS,
            katex_js=KATEX_JS,
            auto_render_js=AUTO_RENDER_JS,
            content=setup_md_parser().render(markdown_text),
        )

        async with async_playwright() as p:
            log(f"步骤 2/5: 开始启动无头浏览器预渲染...", 1)
            device_scale_factor = 3
            browser = await p.chromium.launch()
            page = await browser.new_page(device_scale_factor=device_scale_factor)

            log(f"步骤 3/5: 开始加载HTML并等待JavaScript渲染 (KaTeX)...", 1)
            await page.set_content(full_html_to_render)

            log(f"步骤 4/5: 开始处理KaTeX公式（截图并内嵌）...", 1)
            processed_html = await embed_katex_as_base64(page,device_scale_factor)

            await browser.close()

        log(f"步骤 5/5: 执行CSS内联和最终清理...", 1)
        final_html = final_cleanup_and_inline(processed_html)

        log(f"转换流程全部完成!", 1)
        return final_html

    with open(md_file_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    converted_html = await convert(md_text)
    if re.search(r"https?://", md_text):
        logging.critical("检测到 web 链接, 这可能会触发某些邮箱的风控(如QQ邮箱), 使得: 图片无法正常显示, CSS无法正常加载")
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(converted_html)
    print(f"转换后的HTML已保存到 {html_file_path}。")


if __name__ == "__main__":
    try:
        asyncio.run(mailify(sys.argv[1], sys.argv[2]))
    except Exception as e:
        print(f"Error: {e}.")
        exit()
