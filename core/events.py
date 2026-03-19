from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional


class EventType(Enum):
    """事件类型枚举"""
    # 系统事件
    SYSTEM_START = "system_start"
    SYSTEM_SHUTDOWN = "system_shutdown"
    
    # 音频输入事件
    AUDIO_INPUT_START = "audio_input_start"
    AUDIO_INPUT_END = "audio_input_end"
    AUDIO_INPUT_DATA = "audio_input_data"
    
    # 语音活动检测事件
    VAD_START = "vad_start"
    VAD_END = "vad_end"
    
    # 语音识别事件
    STT_START = "stt_start"
    STT_COMPLETE = "stt_complete"
    STT_ERROR = "stt_error"
    
    # 对话事件
    USER_INPUT_RECEIVED = "user_input_received"
    LLM_RESPONSE_RECEIVED = "llm_response_received"
    
    # 文本转语音事件
    TTS_START = "tts_start"
    TTS_COMPLETE = "tts_complete"
    TTS_ERROR = "tts_error"
    
    # 音频输出事件
    AUDIO_OUTPUT_START = "audio_output_start"
    AUDIO_OUTPUT_END = "audio_output_end"
    
    # 用户交互事件
    USER_INTERRUPT = "user_interrupt"
    USER_ACTIVATE = "user_activate"
    USER_DEACTIVATE = "user_deactivate"


@dataclass
class Event:
    """基础事件类"""
    type: EventType
    timestamp: float
    source: str
    data: Optional[Any] = None


# 特定事件类型的便捷构造函数
def create_event(event_type: EventType, source: str, data: Optional[Any] = None) -> Event:
    """创建事件的便捷函数"""
    import time
    return Event(
        type=event_type,
        timestamp=time.time(),
        source=source,
        data=data
    )
