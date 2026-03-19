#!/usr/bin/env python3
"""
桌面语音助手 WebSocket 服务入口文件
"""

import sys
import os
import logging
import asyncio
import json
from pathlib import Path
import websockets

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from core.engine import AssistantEngine
from core.events import EventType
from utils.logger import setup_logger

# 全局变量
clients = set()
engine = None
server_loop = None

async def broadcast_event(event):
    """广播事件给所有连接的客户端"""
    if not clients:
        return
        
    msg = {
        "type": event.type.value,
        "data": event.data or {}
    }
    
    msg_str = json.dumps(msg)
    # 将消息发送给所有客户端
    # 使用 asyncio.gather 并发发送，忽略断开连接等异常
    await asyncio.gather(
        *(client.send(msg_str) for client in clients),
        return_exceptions=True
    )

def on_engine_event(event):
    """引擎事件回调，将其转发到 WebSocket 广播"""
    if server_loop and server_loop.is_running():
        # 在 server_loop 中调度协程，确保跨线程安全
        asyncio.run_coroutine_threadsafe(broadcast_event(event), server_loop)

async def ws_handler(websocket):
    """处理单个 WebSocket 连接"""
    logging.info(f"新客户端连接: {websocket.remote_address}")
    clients.add(websocket)
    
    # 连接建立后发送 ready 状态
    try:
        await websocket.send(json.dumps({
            "type": "system_start",
            "data": {"status": "ready"}
        }))
        
        # 持续监听前端发来的指令
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                logging.info(f"收到前端指令: {msg_type}")
                
                if msg_type == "user_activate" and engine:
                    engine.activate()
                elif msg_type == "user_interrupt" and engine:
                    engine.interrupt()
            except json.JSONDecodeError:
                logging.warning("收到的不是有效的 JSON 数据")
                
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.remove(websocket)
        logging.info(f"客户端断开: {websocket.remote_address}")

async def main():
    global engine, server_loop
    server_loop = asyncio.get_running_loop()
    
    # 初始化日志
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("启动桌面语音助手 (WebSocket 模式)...")
    
    # 初始化并启动核心引擎
    engine = AssistantEngine()
    
    # 订阅所有我们关心的事件，转发到 WebSocket
    for event_type in EventType:
        engine.dispatcher.subscribe(event_type, on_engine_event)
        
    # 启动引擎
    engine.start()
    
    # 启动 WebSocket 服务器
    host = "127.0.0.1"
    port = 8000
    logger.info(f"正在启动 WebSocket 服务 ws://{host}:{port}/ws ...")
    
    # 启动服务并保持运行
    async with websockets.serve(ws_handler, host, port):
        await asyncio.Future()  # 永久运行

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n收到退出信号，正在停止服务...")
        if engine:
            engine.stop()
        
        # 清理临时文件
        for temp_file in ["temp_input.wav", "temp_output.mp3"]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        print("服务已停止。")