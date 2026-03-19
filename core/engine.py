from typing import Dict, Any, Optional
import time
import threading
import asyncio
from .events import Event, EventType, create_event
from .state_machine import StateMachine, AssistantState
from .dispatcher import EventDispatcher


class AssistantEngine:
    """语音助手核心引擎"""
    
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.state_machine = StateMachine()
        self.dispatcher = EventDispatcher()
        self.running = False
        self.event_loop_thread: Optional[threading.Thread] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 注册状态机事件处理
        self._register_state_event_handlers()
        
        # 注册核心事件处理
        self._register_core_event_handlers()
    
    def _register_state_event_handlers(self):
        """注册状态转换的事件处理"""
        # 注册状态进入处理函数
        self.state_machine.state_handlers[AssistantState.IDLE] = self._on_enter_idle
        self.state_machine.state_handlers[AssistantState.LISTENING] = self._on_enter_listening
        self.state_machine.state_handlers[AssistantState.RECOGNIZING] = self._on_enter_recognizing
        self.state_machine.state_handlers[AssistantState.PROCESSING] = self._on_enter_processing
        self.state_machine.state_handlers[AssistantState.SPEAKING] = self._on_enter_speaking
        self.state_machine.state_handlers[AssistantState.ERROR] = self._on_enter_error
    
    def _register_core_event_handlers(self):
        """注册核心事件处理函数"""
        # 系统事件
        self.dispatcher.subscribe(EventType.SYSTEM_START, self._handle_system_start)
        self.dispatcher.subscribe(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
        
        # 用户交互事件
        self.dispatcher.subscribe(EventType.USER_ACTIVATE, self._handle_user_activate)
        self.dispatcher.subscribe(EventType.USER_DEACTIVATE, self._handle_user_deactivate)
        
        # 音频和语音处理事件
        self.dispatcher.subscribe(EventType.VAD_START, self._handle_vad_start)
        self.dispatcher.subscribe(EventType.VAD_END, self._handle_vad_end)
        self.dispatcher.subscribe(EventType.STT_COMPLETE, self._handle_stt_complete)
        self.dispatcher.subscribe(EventType.LLM_RESPONSE_RECEIVED, self._handle_llm_response)
        self.dispatcher.subscribe(EventType.AUDIO_OUTPUT_END, self._handle_audio_output_end)
    
    def _handle_system_start(self, event: Event):
        """处理系统启动事件"""
        self.running = True
        self.dispatcher.publish(create_event(
            EventType.USER_ACTIVATE,
            source="engine"
        ))
    
    def _handle_system_shutdown(self, event: Event):
        """处理系统关闭事件"""
        self.running = False
        self.stop()
    
    def _handle_user_activate(self, event: Event):
        """处理用户激活事件"""
        self.state_machine.process_event(event)
    
    def _handle_user_deactivate(self, event: Event):
        """处理用户停用事件"""
        self.state_machine.process_event(event)
    
    def _handle_vad_start(self, event: Event):
        """处理语音活动开始事件"""
        self.state_machine.process_event(event)
    
    def _handle_vad_end(self, event: Event):
        """处理语音活动结束事件"""
        # 如果当前在说话状态，支持打断
        if self.state_machine.current_state == AssistantState.SPEAKING:
            # 发布打断事件
            self.dispatcher.publish(create_event(
                EventType.USER_INTERRUPT,
                source="engine",
                data={"reason": "vad_detected"}
            ))
    
    def _handle_stt_complete(self, event: Event):
        """处理语音识别完成事件"""
        self.state_machine.process_event(event)
        # 发布用户输入接收事件
        self.dispatcher.publish(create_event(
            EventType.USER_INPUT_RECEIVED,
            source="engine",
            data={"text": event.data.get("text")}
        ))
    
    def _handle_llm_response(self, event: Event):
        """处理大模型响应事件"""
        self.state_machine.process_event(event)
    
    def _handle_audio_output_end(self, event: Event):
        """处理音频输出结束事件"""
        self.state_machine.process_event(event)
    
    def _on_enter_idle(self):
        """进入空闲状态"""
        self.dispatcher.publish(create_event(
            EventType.SYSTEM_SHUTDOWN,
            source="state_machine"
        ))
    
    def _on_enter_listening(self):
        """进入监听状态"""
        self.dispatcher.publish(create_event(
            EventType.AUDIO_INPUT_START,
            source="state_machine"
        ))
    
    def _on_enter_recognizing(self):
        """进入语音识别状态"""
        self.dispatcher.publish(create_event(
            EventType.STT_START,
            source="state_machine"
        ))
    
    def _on_enter_processing(self):
        """进入处理状态"""
        pass  # 由具体的事件处理函数处理
    
    def _on_enter_speaking(self):
        """进入说话状态"""
        self.dispatcher.publish(create_event(
            EventType.TTS_START,
            source="state_machine"
        ))
    
    def _on_enter_error(self):
        """进入错误状态"""
        pass
    
    def start(self):
        """启动引擎"""
        if self.running:
            return
        
        self.running = True
        
        # 创建并启动事件循环线程
        self.event_loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.event_loop_thread.start()
        
        # 等待事件循环初始化
        while self.event_loop is None:
            time.sleep(0.1)
        
        # 发布系统启动事件
        self.dispatcher.publish(create_event(
            EventType.SYSTEM_START,
            source="engine"
        ))
    
    def _run_event_loop(self):
        """运行事件循环"""
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        
        try:
            self.event_loop.run_forever()
        except Exception as e:
            print(f"事件循环错误: {e}")
        finally:
            self.event_loop.close()
    
    def stop(self):
        """停止引擎"""
        self.running = False
        
        if self.event_loop and not self.event_loop.is_closed():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        
        if self.event_loop_thread and self.event_loop_thread.is_alive():
            self.event_loop_thread.join(timeout=1.0)
    
    def publish_event(self, event: Event):
        """发布事件"""
        self.dispatcher.publish(event)
    
    def publish_event_async(self, event: Event):
        """异步发布事件"""
        self.dispatcher.publish_async(event)
    
    def subscribe_event(self, event_type: EventType, handler):
        """订阅事件"""
        self.dispatcher.subscribe(event_type, handler)
    
    def unsubscribe_event(self, event_type: EventType, handler):
        """取消订阅事件"""
        self.dispatcher.unsubscribe(event_type, handler)
    
    def get_current_state(self) -> AssistantState:
        """获取当前状态"""
        return self.state_machine.current_state
    
    def activate(self):
        """激活助手"""
        self.dispatcher.publish(create_event(
            EventType.USER_ACTIVATE,
            source="engine"
        ))
    
    def deactivate(self):
        """停用助手"""
        self.dispatcher.publish(create_event(
            EventType.USER_DEACTIVATE,
            source="engine"
        ))
    
    def interrupt(self):
        """打断当前操作"""
        self.dispatcher.publish(create_event(
            EventType.USER_INTERRUPT,
            source="engine"
        ))
