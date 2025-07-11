# md-mailify
轻松将md文件转化为浏览器渲染后的html文件


markdown 渲染（支持latex、代码块(支持代码高亮)）
支持自定义 css 美化（可能会有些许误差）

一行命令得到可直接在email使用的html文件，

修改配置每次保存时可以通过vscode实时预览效果。

你要写邮件？要给导师写信？
还不快用 md_mailify 炫染你的 E妹儿，发给你心仪的老登迷死他/她。

针对电脑和手机显示做了优化

自动处理远程和本地图片

使用
- `mailify-md  ./a.md` 会输出为./a.html
- `mailify-md  ./a.md ./dir/` 会输出为./dir/a.html
- `mailify-md  ./a.md ./dir/b.html` 会输出为./dir/b.html

可选项：
- 修改主题样式：`-t light`、`-t dark`、`-t 自定义css文件路径`（或者用`--theme`）
（tip：参考rsc/light_style_bak.css和rsc/dark_style_bak.css 设置）




