import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
RSCDIR = os.path.join(ROOT_DIR, "rsc")

BUILT_IN_CSS = {
    "KATEX_MIN_CSS": None,
    "BASE_CSS": None,
}
BUILT_IN_JS = {
    "KATEX_MIN_JS": None,
    "AUTO_RENDER_MIN_JS": None,
    "BASE_JS": None,
}
CUSTOM_CSS = None

# region: BUILT_IN_CSS
with open(os.path.join(RSCDIR, "katex.min.css"), "r", encoding="utf-8") as f:
    BUILT_IN_CSS["KATEX_MIN_CSS"] = f.read()

BUILT_IN_CSS[
    "BASE_CSS"
] = """
/* 代码块内的代码不要有行内代码的灰框 */
div.container pre>code {{  
    background-color: transparent;
    font-weight: 600;
}}
"""
# endregion

# region: BUILT_IN_JS
with open(os.path.join(RSCDIR, "katex.min.js"), "r", encoding="utf-8") as f:
    BUILT_IN_JS["KATEX_MIN_JS"] = f.read()
# KaTeX CSS: 使用经过处理、内联了Base64字体的版本
with open(os.path.join(RSCDIR, "katex.inlined.css"), "r", encoding="utf-8") as f:
    BUILT_IN_CSS["KATEX_INLINED_CSS"] = f.read()
with open(os.path.join(RSCDIR, "auto-render.min.js"), "r", encoding="utf-8") as f:
    BUILT_IN_JS["AUTO_RENDER_MIN_JS"] = f.read()

BUILT_IN_JS[
    "BASE_JS"
] = """
document.addEventListener("DOMContentLoaded", function () {
                renderMathInElement(document.body, {
                    delimiters: [
                        { left: '$$', right: '$$', display: true },
                        { left: '$', right: '$', display: false },
                        { left: '\\(', right: '\\)', display: false },
                        { left: '\\[', right: '\\]', display: true }
                    ]
                });
            });
"""
# endregion

# region: CUSTOM_CSS
with open(os.path.join(ROOT_DIR, "style.css"), "r", encoding="utf-8") as f:
    CODE_STYLE = f.readline().strip().split(":")[1][:-3].strip()
    CUSTOM_CSS = f.read()
# endregion


# --- 资源文件 ---
# 为了创建单个独立的HTML文件，所有CSS和JS都以内联方式读入



# KaTeX JS
# ... existing code ...
# KaTeX JS 和 自动渲染插件
with open(os.path.join(ROOT_DIR, "rsc", "katex.min.js"), "r", encoding="utf-8") as f:
    KATEX_JS = f.read()
with open(os.path.join(ROOT_DIR, "rsc", "auto-render.min.js"), "r", encoding="utf-8") as f:
    AUTO_RENDER_JS = f.read()


# --- HTML模板 ---
# 该模板包含了所有必要的CSS和JS, 使用 .format() 方法进行填充
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <title>湖大姻缘一线牵，珍惜这段缘</title>
    <meta charset="utf-8">
    <meta content="width=device-width, initial-scale=1.0" name="viewport">
    <style>{katex_css}</style>
    <style>{custom_css}</style>
</head>
<body>
    <div class="container">
        <!--主题内容输入到这里-->
        {content}
    </div>
    <div class="scripts">
        <script>{katex_js}</script>
        <script>{auto_render_js}</script>
        <script>
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "$", right: "$", display: false}},
                    {{left: "\\\\[", right: "\\\\]", display: true}},
                    {{left: "\\\\(", right: "\\\\)", display: false}}
                ]
            }});
        </script>
    </div>
</body>
</html>
"""
