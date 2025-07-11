# mailify-md
## 简介
轻松将md文件转化为邮箱环境渲染后的html文件

<img src="./rsc/light_demo.gif" alt="light_demo">
<img src="./rsc/dark_demo.gif" alt="dark_demo">

## 安装
```bash
# 安装包
pip install mailify-md
# 安装浏览器依赖:
playwright install --with-deps
```

## 快速开始
```bash
# 用法一: 在原目录下生成同名 .html 文件
mailify-md test.md

# 用法二: 在指定输出目录下生成同名 .html 文件
mailify-md test.md ./output/

# 用法三: 指定输出文件名字和路径
mailify-md test.md ./output/email.html
```

## 功能特色
- 结果美观:
  - 支持自定义 css 美化
  - 支持latex
  - 支持代码块(支持代码高亮)
  - 针对电脑和手机显示做了优化
- 简单易用:
  - 一行命令得到可直接在email使用的html文件
  - 内置一些精美样式
- 支持全面:
  - 自动处理远程和本地图片
  - 支持svg, gif, png等各种图片格式自动内嵌(无需修改你的md文件中的路径)

## 命令行用法

`mailify-md [OPTIONS] INPUT_PATH [OUTPUT_PATH]`

**参数:**
- `INPUT_PATH`:  必须项，你的 Markdown 文件路径。
- `OUTPUT_PATH`: 可选项，可以是输出目录或完整的文件路径。
  - 如果是目录，则输出文件名与输入文件相同。
  - 如果省略，则输出在输入文件旁边。

**可选项:**
- `-t, --theme TEXT`:  设置主题。可以是 `light`, `dark`, 或一个自定义 CSS 文件的路径。
  - 示例: `mailify-md test.md -t dark`
  - 示例: `mailify-md test.md -t ./my-style.css`
  - (tip：可参考[内置主题css](./src/mailify_md/data/dark_style_bak.css)设置)

## 作为库使用

你也可以在 Python 代码中直接调用 `mailify_md`: `from mailify_md import mailify_md`




<!-- 
<p align="center" style="font-size: 1em; font-style: italic; background: linear-gradient(270deg, #ff8a00, #e52e71, #4a90e2, #43e97b); color: transparent; background-clip: text; font-weight: bold; margin: 4em 0;">
听说你要心仪的老登写邮件？<br>
还不快用 <span style="text-shadow: 0 0 1px rgb(250, 171, 0), 0 0 0px rgb(254, 51, 0);">mailify-md</span> 炫染你的E妹儿，多种花样送给亲。
</p> -->

<p align="center">
    <img src="./rsc/demo.svg" alt="demo" style="max-height: 50px;">
</p>
