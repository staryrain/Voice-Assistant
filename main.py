#!/usr/bin/env python3
"""
桌面语音助手主入口文件 - FSM 状态机模式
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from core.engine import AssistantEngine
from utils.logger import setup_logger

def main():
    """主函数"""
    # 初始化日志
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("启动桌面语音助手 (FSM 模式)...")

    # 初始化并启动核心引擎
    engine = None
    try:
        # 创建引擎实例
        engine = AssistantEngine()
        
        # 启动引擎（开启事件循环线程）
        engine.start()
        
        print("\n" + "="*40)
        print("      语音助手已就绪 (状态机模式)")
        print("="*40)
        print("\n控制指令:")
        print("  [a] - 激活助手 (模拟唤醒)")
        print("  [i] - 打断助手 (模拟语音打断)")
        print("  [d] - 停用助手 (回到待机状态)")
        print("  [q] - 退出程序")
        print("-" * 40)

        while True:
            try:
                cmd = input("\n请输入指令: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd == 'q':
                logger.info("用户请求退出")
                break
            elif cmd == 'a':
                logger.info("手动触发激活")
                engine.activate()
            elif cmd == 'i':
                logger.info("手动触发打断")
                engine.interrupt()
            elif cmd == 'd':
                logger.info("手动触发停用")
                engine.deactivate()
            elif cmd == '':
                continue
            else:
                print(f"未知指令: '{cmd}'。可用指令: a, i, d, q")

    except Exception as e:
        logger.exception(f"程序运行发生致命错误: {e}")
    finally:
        if engine:
            logger.info("正在停止引擎...")
            engine.stop()
        
        # 清理临时文件
        for temp_file in ["temp_input.wav", "temp_output.mp3"]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        logger.info("程序已安全退出。")

if __name__ == "__main__":
    main()
