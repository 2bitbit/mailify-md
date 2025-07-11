from pathlib import Path
import re

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
BUILTINS_DIR = DATA_DIR / "builtins"

MAIN_CONTAINER_CLASS = "md_content_to_mailify"

# region: BUILT_IN_CSS
BUILT_IN_CSS = "\n".join(
    [
        (BUILTINS_DIR / "katex.inlined.css").read_text(encoding="utf-8"),
    ]
)
# endregion

# region: BUILT_IN_JS
BUILT_IN_JS = "\n".join(
    [
        (BUILTINS_DIR / "katex.min.js").read_text(encoding="utf-8"),
        (BUILTINS_DIR / "auto-render.min.js").read_text(encoding="utf-8"),
        (BUILTINS_DIR / "base.js").read_text(encoding="utf-8"),
    ]
)
# endregion


# region: HTML_TEMPLATE
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <title>湖大姻缘一线牵，珍惜这段缘</title>
    <meta charset="utf-8">
    <meta content="width=device-width, initial-scale=1.0" name="viewport">
    <style>{BUILTIN_CSS}</style>
    <style>{THEME_STYLE}</style>
</head>
<body>
    <div class="{MAIN_CONTENT_CLASS}">
        <!-- HTML 内容输入到这里-->
        {content}
    </div>
    
    <script>{BUILTIN_JS}</script>
</body>
</html>
"""
# endregion
