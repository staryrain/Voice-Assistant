from enum import Enum
from typing import Dict, List, Optional
from .events import Event, EventType


class AssistantState(Enum):
    """语音助手状态枚举"""
    # 空闲状态：等待用户激活
    IDLE = "idle"
    
    # 监听状态：等待用户说话
    LISTENING = "listening"
    
    # 语音识别状态：正在将语音转换为文本
    RECOGNIZING = "recognizing"
    
    # 处理状态：正在与大模型交互
    PROCESSING = "processing"
    
    # 说话状态：正在播放TTS语音
    SPEAKING = "speaking"
    
    # 错误状态：处理错误情况
    ERROR = "error"


class Transition:
    """状态转换定义"""
    def __init__(self, from_state: AssistantState, to_state: AssistantState, event_type: EventType):
        self.from_state = from_state
        self.to_state = to_state
        self.event_type = event_type


class StateMachine:
    """语音助手状态机"""
    
    def __init__(self):
        self.current_state = AssistantState.IDLE
        self.transitions = self._define_transitions()
        self.state_handlers = self._define_state_handlers()
        self.event_handlers = {}
    
    def _define_transitions(self) -> List[Transition]:
        """定义状态转换规则"""
        return [
            # 从空闲状态转换
            Transition(AssistantState.IDLE, AssistantState.LISTENING, EventType.USER_ACTIVATE),
            Transition(AssistantState.IDLE, AssistantState.LISTENING, EventType.SYSTEM_START),
            
            # 从监听状态转换
            Transition(AssistantState.LISTENING, AssistantState.RECOGNIZING, EventType.VAD_START),
            Transition(AssistantState.LISTENING, AssistantState.IDLE, EventType.USER_DEACTIVATE),
            
            # 从语音识别状态转换
            Transition(AssistantState.RECOGNIZING, AssistantState.PROCESSING, EventType.STT_COMPLETE),
            Transition(AssistantState.RECOGNIZING, AssistantState.LISTENING, EventType.STT_ERROR),
            Transition(AssistantState.RECOGNIZING, AssistantState.LISTENING, EventType.USER_INTERRUPT),
            
            # 从处理状态转换
            Transition(AssistantState.PROCESSING, AssistantState.SPEAKING, EventType.LLM_RESPONSE_RECEIVED),
            Transition(AssistantState.PROCESSING, AssistantState.LISTENING, EventType.USER_INTERRUPT),
            
            # 从说话状态转换
            Transition(AssistantState.SPEAKING, AssistantState.LISTENING, EventType.AUDIO_OUTPUT_END),
            Transition(AssistantState.SPEAKING, AssistantState.RECOGNIZING, EventType.VAD_START),  # 支持打断
            Transition(AssistantState.SPEAKING, AssistantState.LISTENING, EventType.USER_DEACTIVATE),
            
            # 从错误状态转换
            Transition(AssistantState.ERROR, AssistantState.IDLE, EventType.USER_ACTIVATE),
        ]
    
    def _define_state_handlers(self) -> Dict[AssistantState, callable]:
        """定义状态进入时的处理函数"""
        return {
            AssistantState.IDLE: self._on_enter_idle,
            AssistantState.LISTENING: self._on_enter_listening,
            AssistantState.RECOGNIZING: self._on_enter_recognizing,
            AssistantState.PROCESSING: self._on_enter_processing,
            AssistantState.SPEAKING: self._on_enter_speaking,
            AssistantState.ERROR: self._on_enter_error,
        }
    
    def _on_enter_idle(self):
        """进入空闲状态的处理"""
        pass
    
    def _on_enter_listening(self):
        """进入监听状态的处理"""
        pass
    
    def _on_enter_recognizing(self):
        """进入语音识别状态的处理"""
        pass
    
    def _on_enter_processing(self):
        """进入处理状态的处理"""
        pass
    
    def _on_enter_speaking(self):
        """进入说话状态的处理"""
        pass
    
    def _on_enter_error(self):
        """进入错误状态的处理"""
        pass
    
    def process_event(self, event: Event) -> bool:
        """处理事件并执行状态转换"""
        # 查找匹配的状态转换
        for transition in self.transitions:
            if (transition.from_state == self.current_state and 
                transition.event_type == event.type):
                
                # 执行状态转换
                self.current_state = transition.to_state
                
                # 调用状态进入处理函数
                if self.current_state in self.state_handlers:
                    self.state_handlers[self.current_state]()
                
                # 调用事件处理函数
                if event.type in self.event_handlers:
                    self.event_handlers[event.type](event)
                
                return True
        
        # 没有找到匹配的转换
        return False
    
    def register_event_handler(self, event_type: EventType, handler: callable):
        """注册事件处理函数"""
        self.event_handlers[event_type] = handler
    
    def get_current_state(self) -> AssistantState:
        """获取当前状态"""
        return self.current_state
    
    def set_state(self, state: AssistantState):
        """直接设置状态"""
        self.current_state = state
        if state in self.state_handlers:
            self.state_handlers[state]()
