# -*- coding: utf-8 -*-
import logging, re, base64, requests
from pathlib import Path
from .utils import log, contains_web_links
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup
from cairosvg import svg2png
from playwright.async_api import async_playwright, Page
from premailer import Premailer
from .CONSTANTS import DATA_DIR, BUILTINS_DIR, MAIN_CONTAINER_CLASS, HTML_TEMPLATE, BUILT_IN_CSS, BUILT_IN_JS


class MailifyMD:
    """
    将 Markdown 转换为邮件优化的 HTML。

    工作流程:
    1. 解析 md:          MarkdownIt (pygments_highlighter) 解析 md -> HTML, 嵌入 HTML 模板中。生成 soup 用于预处理
    2. 本地和远程图片:    soup预处理: (如果是远程图片,requests来拉取,)把<img>标签的src属性替换为base64编码的png,gif等图片(如果是svg,用cairosvg转成png)
    3. 预渲染:           Playwright 预渲染Katex公式, 并计算css。此阶段如果还有其他非data图片, 发出警告。
    4. 内联化:           使用 Premailer 对page.content()处理, 将所有 <style> 规则内联到 HTML 元素中, 并清理 <script>

    - 通过修改 theme_css, 来设置theme_style和code_style
    """

    def __init__(self, input_md_fpath: str, output_html_fpath: str, theme_css: str):
        self.input_md_fpath = Path(input_md_fpath).resolve()
        self.output_html_fpath = Path(output_html_fpath).resolve()
        self.theme_style, self.code_style = self._get_theme_style_and_code_style(theme_css)

    async def run(self):
        md_text = self.input_md_fpath.read_text(encoding="utf-8")
        if contains_web_links(md_text):
            logging.warning(
                "检测到 md 本身含有网站链接, 这可能会触发某些邮箱的风控(如QQ邮箱): 使得图片无法正常显示, CSS无法正常加载"
            )
        converted_html = await self._convert(md_text)
        self.output_html_fpath.write_text(converted_html, encoding="utf-8")
        print(f"转换后的HTML已保存到 {self.output_html_fpath}。")

    async def _convert(self, markdown_text: str) -> str:
        """
        执行从Markdown到邮件优化HTML的完整转换流程。
        """
        log(f"开始将Markdown转换为HTML", 0)
        soup = BeautifulSoup(self._get_full_html(self._setup_md_parser().render(markdown_text)), "html.parser")

        async with async_playwright() as p:
            log(f"开始用base64内嵌本地和远程图片", 1)
            soup = await self._embed_images_as_base64(soup)
            log(f"开始预渲染(计算css, 处理KaTeX公式等操作)", 1)
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(str(soup))
            await page.wait_for_load_state("load")  # 等待页面加载完成
            log(f"移除<script>标签并进行 CSS 内联化...", 1)
            final_html = self._final_cleanup_and_inline(await page.content())

        log(f"转换流程全部完成!", 1)
        return final_html

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

    async def _embed_images_as_base64(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        在BeautifulSoup对象中查找<img>标签, 并使用预先拦截的图片数据将其替换为Base64。
        如果图片是SVG, 则用cairosvg将其转换为PNG。

        Args:
            soup: BeautifulSoup 解析后的HTML对象。
            page: Playwright 页面对象, 用于查找和截图SVG图片。
        Returns:
            修改后的 BeautifulSoup 对象。
        """
        from html import unescape

        img_tags = soup.select("img:not([src^='data'])")
        # 样例： <img src="https://img.shields.io/badge/PyTorch-FF6B00" alt="PyTorch" />、<img src='./logo.svg' />
        for img_tag in img_tags:
            # BeautifulSoup 可能会保留HTML实体编码 (如 &amp;), 所以我们需要反转义以匹配网络请求中的URL
            image_src = unescape(str(img_tag.get("src") or "")).strip()
            if not image_src:
                logging.error(f"警告: 图片标签{img_tag}没有src属性, 跳过")
                continue
            elif image_src.startswith("http"):  # 远程图片
                response = requests.get(image_src)
                image_bytes = response.content
                media_type = response.headers["Content-Type"]
            else:  # 本地图片
                image_path = Path(image_src)
                if not image_path.is_absolute():  # 处理相对路径
                    image_path = self.input_md_fpath.parent / image_path
                image_bytes = image_path.read_bytes()
                media_type = "image/" + image_path.suffix.lower()[1:]

            if media_type.startswith("image/svg"):  # 处理svg图片
                image_bytes = svg2png(bytestring=image_bytes)
                assert image_bytes
                media_type = "image/png"

            img_tag["src"] = f"data:{media_type};base64,{base64.b64encode(image_bytes).decode()}"
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
            keep_style_tags=True,
            cssutils_logging_level="CRITICAL",
        )
        return premailer.transform()

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
            BUILTIN_CSS=BUILT_IN_CSS,
            THEME_STYLE=self.theme_style,
            MAIN_CONTENT_CLASS=MAIN_CONTAINER_CLASS,
            content=content_html,
            BUILTIN_JS=BUILT_IN_JS,
        )
