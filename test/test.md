# 一份包含代码和公式的报告

这是一个**演示**，*展示*了如何将Markdown、代码和数学公式转换为一封***精美的***HTML邮件。

## 链接
- [百度](https://www.baidu.com) 指向 https://www.baidu.com
- [谷歌](https://www.google.com) 指向 https://www.google.com


## 代码高亮

下面是2个代码示例，它会被 `Pygments` 自动高亮。

```python
def greet(name: str):
    # 这只是一个简单的问候函数
    print(f"Hello, {name}! Welcome to the world of advanced email generation.")

greet("Developer")
```
```js
const a = 1;
const b = 2;
const c = a + b;
console.log(`c: ${c}`);
```

语言未知
```unknown-language
println("Hello, World!")
```

语言为空
```
println("Hello, World!")
```

## 数学公式渲染
质能方程 $E=mc^2$ 是爱因斯坦的著名公式。

著名的高斯积分：
$$
\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}
$$

## md中html的支持
<p style="text-align: center;color: green;">这是内联居中的文字</p>