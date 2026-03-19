import unittest
from core.state_machine import StateMachine, AssistantState, Transition
from core.events import EventType, Event, create_event


class TestStateMachine(unittest.TestCase):
    """测试状态机功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.state_machine = StateMachine()
    
    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.IDLE)
    
    def test_state_transitions(self):
        """测试状态转换"""
        # 从IDLE到LISTENING
        event = create_event(EventType.USER_ACTIVATE, "test_source")
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.LISTENING)
        
        # 从LISTENING到RECOGNIZING
        event = create_event(EventType.VAD_START, "test_source")
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.RECOGNIZING)
        
        # 从RECOGNIZING到PROCESSING
        event = create_event(EventType.STT_COMPLETE, "test_source", {"text": "你好"})
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.PROCESSING)
        
        # 从PROCESSING到SPEAKING
        event = create_event(EventType.LLM_RESPONSE_RECEIVED, "test_source", {"text": "你好，我是语音助手"})
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.SPEAKING)
        
        # 从SPEAKING到LISTENING
        event = create_event(EventType.AUDIO_OUTPUT_END, "test_source")
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.LISTENING)
        
        # 从LISTENING到IDLE
        event = create_event(EventType.USER_DEACTIVATE, "test_source")
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.IDLE)
    
    def test_interrupt_transitions(self):
        """测试中断转换"""
        # 测试在RECOGNIZING状态下中断
        self.state_machine.set_state(AssistantState.RECOGNIZING)
        event = create_event(EventType.USER_INTERRUPT, "test_source")
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.LISTENING)
        
        # 测试在PROCESSING状态下中断
        self.state_machine.set_state(AssistantState.PROCESSING)
        event = create_event(EventType.USER_INTERRUPT, "test_source")
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.LISTENING)
    
    def test_speaking_interruption(self):
        """测试说话状态下的中断"""
        # 从SPEAKING到RECOGNIZING（用户打断）
        self.state_machine.set_state(AssistantState.SPEAKING)
        event = create_event(EventType.VAD_START, "test_source")
        result = self.state_machine.process_event(event)
        self.assertTrue(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.RECOGNIZING)
    
    def test_invalid_transition(self):
        """测试无效的状态转换"""
        # 在IDLE状态下发送VAD_START事件
        event = create_event(EventType.VAD_START, "test_source")
        result = self.state_machine.process_event(event)
        self.assertFalse(result)
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.IDLE)
    
    def test_event_handler_registration(self):
        """测试事件处理函数注册"""
        handled = False
        event_data = None
        
        def test_handler(event):
            nonlocal handled, event_data
            handled = True
            event_data = event.data
        
        # 注册事件处理函数
        self.state_machine.register_event_handler(EventType.USER_ACTIVATE, test_handler)
        
        # 发送事件
        event = create_event(EventType.USER_ACTIVATE, "test_source", {"test": "data"})
        self.state_machine.process_event(event)
        
        # 验证事件处理函数被调用
        self.assertTrue(handled)
        self.assertEqual(event_data, {"test": "data"})
    
    def test_state_handler_call(self):
        """测试状态处理函数调用"""
        entered_listening = False
        
        def on_enter_listening():
            nonlocal entered_listening
            entered_listening = True
        
        # 注册状态处理函数
        self.state_machine.state_handlers[AssistantState.LISTENING] = on_enter_listening
        
        # 触发状态转换到LISTENING
        event = create_event(EventType.USER_ACTIVATE, "test_source")
        self.state_machine.process_event(event)
        
        # 验证状态处理函数被调用
        self.assertTrue(entered_listening)
    
    def test_direct_state_setting(self):
        """测试直接设置状态"""
        # 直接设置状态到PROCESSING
        entered_processing = False
        
        def on_enter_processing():
            nonlocal entered_processing
            entered_processing = True
        
        self.state_machine.state_handlers[AssistantState.PROCESSING] = on_enter_processing
        self.state_machine.set_state(AssistantState.PROCESSING)
        
        # 验证状态和处理函数
        self.assertEqual(self.state_machine.get_current_state(), AssistantState.PROCESSING)
        self.assertTrue(entered_processing)


class TestTransition(unittest.TestCase):
    """测试状态转换定义"""
    
    def test_transition_creation(self):
        """测试转换创建"""
        transition = Transition(
            from_state=AssistantState.IDLE,
            to_state=AssistantState.LISTENING,
            event_type=EventType.USER_ACTIVATE
        )
        
        self.assertEqual(transition.from_state, AssistantState.IDLE)
        self.assertEqual(transition.to_state, AssistantState.LISTENING)
        self.assertEqual(transition.event_type, EventType.USER_ACTIVATE)


if __name__ == "__main__":
    unittest.main()
