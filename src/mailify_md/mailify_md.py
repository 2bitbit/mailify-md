# -*- coding: utf-8 -*-
import sys, logging, asyncio, re, base64, pathlib
from pathlib import Path
from .utils import log, trim_image_by_color
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright, Page, Response
from premailer import Premailer
from .CONSTANTS import DATA_DIR, BUILTINS_DIR, MAIN_CONTAINER_CLASS, HTML_TEMPLATE, BUILT_IN_CSS, BUILT_IN_JS

"""
将 Markdown 转换为邮件优化的 HTML。

工作流程:
1. MarkdownIt (pygments_highlighter) 解析 md -> HTML, 嵌入 HTML 模板中
2. Playwright 预渲染 Katex 公式并截图裁剪, 并拦截远程图片。
3. 结合 BeautifulSoup 将 KatexHTML, 本地和远程图片 -> 替换为带有Base64数据的<img>标签
4. 使用 Premailer 将所有 <style> 规则内联到 HTML 元素中, 并进行最终清理

- 通过修改 theme_css, 来设置theme_style和code_style
"""


class MailifyMD:
    def __init__(self, input_md_fpath: str, output_html_fpath: str, theme_css: str):
        self.input_md_fpath = Path(input_md_fpath).resolve()
        self.output_html_fpath = Path(output_html_fpath).resolve()
        self.theme_style, self.code_style = self._get_theme_style_and_code_style(theme_css)
        self.device_scale_factor = 3

    async def run(self):
        with open(self.input_md_fpath, "r", encoding="utf-8") as f:
            md_text = f.read()
        converted_html = await self._convert(md_text)
        if re.search(r"https?://", md_text):
            logging.error(
                "检测到 md 本身含有网站链接, 这可能会触发某些邮箱的风控(如QQ邮箱): 使得图片无法正常显示, CSS无法正常加载"
            )
        with open(self.output_html_fpath, "w", encoding="utf-8") as f:
            f.write(converted_html)
        print(f"转换后的HTML已保存到 {self.output_html_fpath}。")

    def _setup_md_parser(self) -> MarkdownIt:
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
                    style=self.code_style,
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

    async def _embed_katex_as_base64(self, soup: BeautifulSoup, page: Page) -> BeautifulSoup:
        """在Playwright页面中查找KaTeX元素, 截图裁剪并替换为Base64内嵌的img标签。"""
        katex_containers = await page.query_selector_all(".katex-display, :not(.katex-display)>.katex")
        bs_containers = soup.select(".katex-display, :not(.katex-display)>.katex")
        if not katex_containers:
            logging.info("未找到KaTeX公式, 跳过截图替换公式步骤。")
            return soup
        if len(katex_containers) != len(bs_containers):
            raise ValueError("KaTeX元素数量与BeautifulSoup元素数量不一致, 跳过截图替换公式步骤。")

        async def get_container_background_rgb_color() -> list[int]:
            """动态获取容器背景色, 用于后续的精确裁切"""
            container_element = await page.query_selector(f".{MAIN_CONTAINER_CLASS}")
            assert container_element is not None
            background_color_rgb_str = await container_element.evaluate(
                "el => window.getComputedStyle(el).backgroundColor"
            )
            match = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d\.]+)?\)", background_color_rgb_str)
            if match:
                lst = [int(match.group(1)), int(match.group(2)), int(match.group(3))]
                if len(match.groups()) == 4:
                    lst.append(int(match.group(4)))
                else:
                    lst.append(255)
                return lst
            else:
                raise ValueError(f"无法解析背景色: {background_color_rgb_str}")

        log(f"找到 {len(bs_containers)} 个KaTeX数学公式, 开始进行截图和Base64内嵌...")
        for i in range(len(bs_containers)):
            kt_container, bs_container = katex_containers[i], bs_containers[i]
            is_display_formula = await kt_container.evaluate("el => el.classList.contains('katex-display')")

            # 统一处理：始终截图内部的 .katex-html 元素。
            element_to_screenshot = await kt_container.query_selector(".katex-html")
            if not element_to_screenshot:
                raise ValueError("KaTeX公式截图元素不存在")

            # 使用基于颜色对比的算法裁切截图中的空白区域
            trimmed_bytes, physical_width = trim_image_by_color(
                await element_to_screenshot.screenshot(type="png"),
                await get_container_background_rgb_color(),
            )

            latex_source_tag = bs_container.find("annotation", encoding="application/x-tex")
            assert isinstance(latex_source_tag, Tag)
            alt_content = latex_source_tag.string or ""

            # 将物理像素宽度转换回 CSS 使用的逻辑像素宽度
            css_width = physical_width // self.device_scale_factor

            # 根据公式类型应用不同的样式：块级公式居中显示，行内公式与文本对齐
            if is_display_formula:
                img_style = f"display: block; margin: 0.5em auto; width: {css_width}px; height: auto; max-width: 100%;"
            else:
                img_style = f"width: {css_width}px; height: auto; vertical-align: middle; max-width: 100%;"

            img_tag = soup.new_tag(
                "img",
                src=f"data:image/png;base64,{base64.b64encode(trimmed_bytes).decode()}",
                alt=alt_content,
                style=img_style,
            )
            # 用生成的 <img> 标签替换掉整个公式容器
            bs_container.replace_with(img_tag)
        return soup

    async def _embed_remote_images_as_base64(self, soup: BeautifulSoup, image_cache: dict, page: Page) -> BeautifulSoup:
        """
        在BeautifulSoup对象中查找<img>标签, 并使用预先拦截的图片数据将其替换为Base64。
        如果图片是SVG, 则在页面上精确定位该图片并截图, 将其转换为PNG。

        Args:
            soup: BeautifulSoup 解析后的HTML对象。
            image_cache: 包含 URL -> {body, content_type} 的字典。
            page: Playwright 页面对象, 用于查找和截图SVG图片。
        Returns:
            修改后的 BeautifulSoup 对象。
        """
        from html import unescape

        # 样例： <img src="https://img.shields.io/badge/PyTorch-FF6B00?style=for-the-badge&amp;logo=pytorch&amp;logoColor=white" alt="PyTorch" />
        img_tags = soup.select('img[src^="http"]')
        if not img_tags:
            log("未找到匹配的远程图片, 跳过此步骤。")
            return soup
        else:
            log(f"找到 {len(img_tags)} 个匹配的远程图片, 开始处理")

        for img_tag in img_tags:
            # BeautifulSoup 可能会保留HTML实体编码 (如 &amp;), 所以我们需要反转义以匹配网络请求中的URL
            image_src = unescape(str(img_tag.get("src") or ""))
            if not image_src:
                logging.error(f"警告: 图片标签{img_tag}没有src属性")
                continue

            cached_image = image_cache.get(image_src)
            if not cached_image:
                logging.error(f"警告: 图片 {image_src} 未在网络缓存中找到, 可能下载失败。跳过此图片。")
                continue

            image_bytes = cached_image["body"]
            mime_type = cached_image["content_type"]
            # clientWidth 是元素自身的可见宽度（像素），不是浏览器窗口的宽度。浏览器窗口的宽度可以用 window.innerWidth 表示。
            css_width = await img_element.evaluate("el => el.clientWidth")

            # 为防止是SVG等其他格式, 统一使用Playwright在页面上定位并截图转换为PNG, 以兼容邮箱环境
            img_element = await page.query_selector(f'img[src="{image_src}"]')
            assert img_element
            image_bytes = await img_element.screenshot(type="png")
            mime_type = "image/png"
            new_tag = soup.new_tag(
                "img",
                src=f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}",
                style=f"width: {css_width}px; height: auto",
            )
            # 用生成的 <img> 标签替换掉整个公式容器
            img_tag.replace_with(new_tag)

        return soup

    async def _embed_local_images_as_base64(self, soup: BeautifulSoup, page: Page) -> BeautifulSoup:
        """
        在BeautifulSoup对象中查找<img>标签, 并使用预先拦截的图片数据将其替换为Base64。
        """
        img_tags = soup.select(
            'img:not([src^="http"]):not([src^="data"])'
        )  # 排除远程图片和已经以base64编码的图片，剩下的图片
        if not img_tags:
            log("未检测到需要嵌入的本地图片, 跳过嵌入本地图片步骤。")
            return soup
        else:
            log(f"找到 {len(img_tags)} 个匹配的本地图片, 开始处理")

        for img_tag in img_tags:
            src_attr = str(img_tag.get("src") or "").strip()
            image_src = Path(src_attr)
            if not image_src.is_absolute():  # 处理相对路径
                md_dir = self.input_md_fpath.parent
                image_src = md_dir / src_attr
            mime_type = image_src.suffix.lower()[1:]  # suffix 包含 .前缀
            if not image_src.exists():
                logging.error(f"警告: 图片{img_tag.get('src')}不存在, 跳过。(可以尝试替换图片路径为绝对路径)")
                continue
            if not mime_type:
                logging.error(f"警告: 图片{img_tag.get('src')}没有文件后缀, 跳过。(尝试为图片重命名, 添加合理后缀)")
                continue
            try:
                img_tag["src"] = f"data:{mime_type};base64,{base64.b64encode(image_src.read_bytes()).decode()}"
            except Exception as e:
                logging.error(f"警告: 处理图片 {image_src} 时发生错误: {e}, 跳过。")
                continue
        return soup

    def _final_cleanup_and_inline(self, html_content: str) -> str:
        """内联CSS样式并移除脚本"""
        # 移除脚本
        soup = BeautifulSoup(html_content, "html.parser")
        for script_tag in soup.find_all("script"):
            script_tag.decompose()
        html_content = str(soup)

        # 内联CSS样式
        premailer = Premailer(
            html_content,
            remove_classes=False,
            keep_style_tags=False,
            cssutils_logging_level="CRITICAL",
        )
        return premailer.transform()

    async def _convert(self, markdown_text: str) -> str:
        """
        执行从Markdown到邮件优化HTML的完整转换流程。
        """
        log(f"开始将Markdown转换为HTML", 0)
        full_html_to_render = self._get_full_html(self._setup_md_parser().render(markdown_text))

        async with async_playwright() as p:
            log(f"开始启动无头浏览器预渲染", 1)
            browser = await p.chromium.launch()
            page = await browser.new_page(device_scale_factor=self.device_scale_factor)

            # 通过网络拦截捕获图片资源, 只需下载一次。
            image_cache = {}

            async def intercept_response(response: Response):
                # 我们只关心成功的图片请求
                if response.request.resource_type == "image" and response.ok:
                    image_cache[response.url] = {
                        "body": await response.body(),
                        "content_type": response.headers.get("content-type", "").split(";")[0],
                    }

            page.on("response", intercept_response)

            # 设置内容
            await page.set_content(full_html_to_render)
            # 等待页面加载完成, 确保所有图片都已触发下载和捕获
            await page.wait_for_load_state("networkidle")

            page.remove_listener("response", intercept_response)

            log("预渲染完成, 启动图片嵌入流程(base64内嵌)", 1)
            soup = BeautifulSoup(await page.content(), "html.parser")  # soup才是最终结果的html，浏览器只是个工具
            log(f"开始处理KaTeX公式", 1)
            soup = await self._embed_katex_as_base64(soup, page)
            log(f"开始处理远程图片", 1)
            soup = await self._embed_remote_images_as_base64(soup, image_cache, page)
            log(f"开始处理本地图片", 1)
            soup = await self._embed_local_images_as_base64(soup)
            await browser.close()

        log(f"执行移除脚本并进行 CSS 内联化...", 1)
        final_html = self._final_cleanup_and_inline(str(soup))

        log(f"转换流程全部完成!", 1)
        return final_html

    def _get_theme_style_and_code_style(self, theme_name_or_fpath: str) -> tuple[str, str]:
        """
        获取内置样式文件代码。
        返回：(主题样式, 代码样式)
        """
        match theme_name_or_fpath:
            case "light":
                theme_fpath = DATA_DIR / "light_style_bak.css"
            case "dark":
                theme_fpath = DATA_DIR / "dark_style_bak.css"
            case _:
                theme_fpath = Path(theme_name_or_fpath)
                if not theme_fpath.exists():
                    raise FileNotFoundError(f"样式文件不存在: {theme_fpath}")
        theme_style = theme_fpath.read_text(encoding="utf-8").strip()
        code_style = re.search(r"CODE_STYLE: *(.*) *\*/", theme_style)
        if code_style is None:
            print("未找到对于CODE_STYLE的定义(参考内置样式文件), 将使用 github-dark 的代码样式")
            code_style = (BUILTINS_DIR / "github-dark.css").read_text(encoding="utf-8").strip()
        else:
            code_style = code_style.group(1).strip()
        return theme_style, code_style

    def _get_full_html(self, content_html: str) -> str:
        return HTML_TEMPLATE.format(
            BUILTIN_CSS="".join(BUILT_IN_CSS),
            THEME_STYLE=self.theme_style,
            MAIN_CONTENT_CLASS=MAIN_CONTAINER_CLASS,
            content=content_html,
            BUILTIN_JS="".join(BUILT_IN_JS),
        )
