"""
DeepSeek 余额桌面小组件 - 主入口
启动桌面小组件，实时显示 DeepSeek 账户余额和消费信息
"""

import sys
import os

# 确保可以导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from widget import DeepSeekWidget


def main():
    """启动 DeepSeek 余额桌面小组件"""
    try:
        widget = DeepSeekWidget()
        widget.run()
    except KeyboardInterrupt:
        print("用户中断，退出...")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 键退出...")


if __name__ == "__main__":
    main()
