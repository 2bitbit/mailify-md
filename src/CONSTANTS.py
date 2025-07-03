HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">

    <title>湖大姻缘一线牵，珍惜这段缘</title>
    <style>
        /* 内置的样式 */
        /* 代码块内的代码不要有行内代码的灰框 */
        div.container pre>code {{  
            background-color: transparent;
            font-weight: 600;
        }}
    </style>
    {style}

</head>

<body>

    <div class="container">
        <!--主题内容输入到这里-->
        {content}
    </div>

    <div class="scripts">
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>

        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>

        <script>
            document.addEventListener("DOMContentLoaded", function () {{
                renderMathInElement(document.body, {{
                    delimiters: [
                        {{ left: '$$', right: '$$', display: true }},
                        {{ left: '$', right: '$', display: false }},
                        {{ left: '\\(', right: '\\)', display: false }},
                        {{ left: '\\[', right: '\\]', display: true }}
                    ]
                }});
            }});
        </script>
    </div>
</body>

</html>
"""

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT_DIR, "style.html"), "r", encoding="utf-8") as f:
    STYLE_HTML = f.read()

IS_TEST = False

CODE_STYLES = ["default", "github-dark", "github-light"]
CODE_STYLE = None
