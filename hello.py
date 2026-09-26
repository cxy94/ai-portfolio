#!/usr/bin/env python3
# hello.py - 验证在 VS Code 中能成功配置并运行 Python 的脚本

import sys


def main():
    print("Hello from ai-portfolio!")
    print("Python 版本：", sys.version.splitlines()[0])
    try:
        import math
        print("math 模��导入成功，示例：math.sqrt(16) =", math.sqrt(16))
    except Exception as e:
        print("导入模块时出错：", e)

    print("如果看到以上输出，说明 VS Code 中的 Python 运行配置正常。")


if __name__ == "__main__":
    main()
