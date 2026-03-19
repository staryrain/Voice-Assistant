import unittest
from datetime import datetime
from core.events import EventType, Event, create_event


class TestEvents(unittest.TestCase):
    """测试事件相关功能"""
    
    def test_event_type_enum(self):
        """测试事件类型枚举值"""
        self.assertEqual(EventType.SYSTEM_START.value, "system_start")
        self.assertEqual(EventType.USER_ACTIVATE.value, "user_activate")
        self.assertEqual(EventType.VAD_START.value, "vad_start")
        self.assertEqual(EventType.STT_COMPLETE.value, "stt_complete")
        self.assertEqual(EventType.LLM_RESPONSE_RECEIVED.value, "llm_response_received")
        self.assertEqual(EventType.AUDIO_OUTPUT_END.value, "audio_output_end")
    
    def test_event_creation(self):
        """测试事件创建"""
        event_type = EventType.USER_INPUT_RECEIVED
        timestamp = 1234567890.123
        source = "test_source"
        data = {"text": "你好"}
        
        event = Event(type=event_type, timestamp=timestamp, source=source, data=data)
        
        self.assertEqual(event.type, event_type)
        self.assertEqual(event.timestamp, timestamp)
        self.assertEqual(event.source, source)
        self.assertEqual(event.data, data)
    
    def test_create_event_function(self):
        """测试create_event函数"""
        event_type = EventType.SYSTEM_START
        source = "test_source"
        data = {"test": "data"}
        
        event = create_event(event_type, source, data)
        
        self.assertEqual(event.type, event_type)
        self.assertEqual(event.source, source)
        self.assertEqual(event.data, data)
        # 检查时间戳是否在合理范围内
        self.assertAlmostEqual(event.timestamp, datetime.now().timestamp(), delta=1.0)
    
    def test_event_without_data(self):
        """测试无数据的事件创建"""
        event = create_event(EventType.SYSTEM_SHUTDOWN, "test_source")
        
        self.assertEqual(event.type, EventType.SYSTEM_SHUTDOWN)
        self.assertIsNone(event.data)


if __name__ == "__main__":
    unittest.main()
