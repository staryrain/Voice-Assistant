from typing import Dict, Any, Optional
import time
import threading
import asyncio
from .events import Event, EventType, create_event
from .state_machine import StateMachine, AssistantState
from .dispatcher import EventDispatcher


from audio.input.stt import STTClient
from audio.output.tts import TTSClient
from audio.output.player import AudioPlayer
from llm.adapter import LLMClient
from audio.input.microphone import record_audio
import os
import logging

logger = logging.getLogger(__name__)

class AssistantEngine:
    """语音助手核心引擎"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        self.settings = settings or {}
        self.state_machine = StateMachine()
        self.dispatcher = EventDispatcher()
        self.running = False
        self.event_loop_thread: Optional[threading.Thread] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 初始化客户端
        self.stt_client = STTClient()
        self.llm_client = LLMClient()
        self.tts_client = TTSClient()
        self.player = AudioPlayer()
        
        # 临时文件路径
        self.temp_audio_input = "temp_input.wav"
        self.temp_audio_output = "temp_output.mp3"
        
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
        self.state_machine.state_handlers[AssistantState.SINGING] = self._on_enter_singing
        self.state_machine.state_handlers[AssistantState.ERROR] = self._on_enter_error
    
    def _register_core_event_handlers(self):
        """注册核心事件处理函数"""
        # 系统事件
        self.dispatcher.subscribe(EventType.SYSTEM_START, self._handle_system_start)
        self.dispatcher.subscribe(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
        
        # 用户交互事件
        self.dispatcher.subscribe(EventType.USER_ACTIVATE, self._handle_user_activate)
        self.dispatcher.subscribe(EventType.USER_DEACTIVATE, self._handle_user_deactivate)
        self.dispatcher.subscribe(EventType.USER_INTERRUPT, self._handle_user_interrupt)
        
        # 业务逻辑触发事件
        self.dispatcher.subscribe(EventType.AUDIO_INPUT_START, self._handle_audio_input_start)
        self.dispatcher.subscribe(EventType.STT_START, self._handle_stt_start)
        self.dispatcher.subscribe(EventType.USER_INPUT_RECEIVED, self._handle_user_input_received)
        self.dispatcher.subscribe(EventType.TTS_START, self._handle_tts_start)
        
        # 音频和语音处理事件
        self.dispatcher.subscribe(EventType.VAD_START, self._handle_vad_start)
        self.dispatcher.subscribe(EventType.VAD_END, self._handle_vad_end)
        self.dispatcher.subscribe(EventType.STT_COMPLETE, self._handle_stt_complete)
        self.dispatcher.subscribe(EventType.STT_ERROR, self._handle_stt_error)
        self.dispatcher.subscribe(EventType.LLM_RESPONSE_RECEIVED, self._handle_llm_response)
        self.dispatcher.subscribe(EventType.AUDIO_OUTPUT_END, self._handle_audio_output_end)
        
        # 音乐事件
        self.dispatcher.subscribe(EventType.MUSIC_START, self._handle_music_start)
        self.dispatcher.subscribe(EventType.MUSIC_END, self._handle_music_end)

    def _handle_system_start(self, event: Event):
        """处理系统启动事件"""
        logger.info("系统启动... (进入待机状态)")
        self.running = True
        
        # 系统启动时，手动触发一次 IDLE 的处理逻辑，以启动唤醒词监听
        self._on_enter_idle()
        
        # 移除自动激活，让程序保持在 IDLE 状态
        # self.dispatcher.publish(create_event(
        #     EventType.USER_ACTIVATE,
        #     source="engine"
        # ))
    
    def _handle_system_shutdown(self, event: Event):
        """处理系统关闭事件"""
        logger.info("系统关闭...")
        self.running = False
        # self.stop() # 避免递归调用
    
    def _handle_user_activate(self, event: Event):
        """处理用户激活事件"""
        logger.info("用户激活助手")
        
        # 防止重复触发唤醒播放
        if getattr(self, '_is_waking_up', False) or self.state_machine.current_state not in (AssistantState.IDLE, AssistantState.ERROR):
            return
            
        self._is_waking_up = True
        
        # 播放唤醒回复并延迟进入监听状态
        def _play_wake_response():
            wake_audio = "test_wakeresponse.mp3"
            if os.path.exists(wake_audio):
                try:
                    logger.info("播放唤醒回复...")
                    self.player.play(wake_audio)
                except Exception as e:
                    logger.error(f"播放唤醒回复失败: {e}")
            
            # 播放完毕后（或文件不存在时）再处理事件进入监听状态
            self._is_waking_up = False
            self.state_machine.process_event(event)
            
        threading.Thread(target=_play_wake_response, daemon=True).start()
    
    def _handle_user_deactivate(self, event: Event):
        """处理用户停用事件"""
        logger.info("用户停用助手")
        self.state_machine.process_event(event)

    def _handle_user_interrupt(self, event: Event):
        """处理用户打断事件"""
        logger.info("用户打断")
        self.state_machine.process_event(event)
        # 停止播放
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            
        # 如果是语音打断，我们可以选择让大模型做出回应
        reason = event.data.get("reason") if event.data else None
        if reason == "voice_interrupt":
            interrupt_text = event.data.get("text", "停下")
            logger.info(f"处理语音打断回应: {interrupt_text}")
            
            # 告诉大模型被用户打断了，并请求一个简短的回应
            def _interrupt_reply_task():
                reply = self.llm_client.chat(f"[系统提示: 用户打断了你的发言，用户说：'{interrupt_text}'。请简短地回应，例如：'好的，我停下了' 或 '好的，有什么新问题吗？']")
                logger.info(f"打断回应: {reply}")
                
                # 再次触发 TTS 播放简短的回应，然后系统会回到 LISTENING
                self.dispatcher.publish(create_event(
                    EventType.TTS_START,
                    source="engine",
                    data={"text": reply}
                ))
                
            threading.Thread(target=_interrupt_reply_task, daemon=True).start()
    
    def _handle_vad_start(self, event: Event):
        """处理语音活动开始事件"""
        logger.info("检测到语音开始...")
        self.state_machine.process_event(event)
    
    def _handle_vad_end(self, event: Event):
        """处理语音活动结束事件"""
        logger.info("检测到语音结束")
        # 如果当前在说话或唱歌状态，支持打断
        if self.state_machine.current_state in (AssistantState.SPEAKING, AssistantState.SINGING):
            self.dispatcher.publish(create_event(
                EventType.USER_INTERRUPT,
                source="engine",
                data={"reason": "vad_detected"}
            ))
    
    def _handle_audio_input_start(self, event: Event):
        """开始录音"""
        def _record_task():
            try:
                # 记录监听开始的时间，用于超时判断
                if not hasattr(self, 'listening_start_time'):
                    self.listening_start_time = time.time()
                
                # 检查是否在 LISTENING 状态超过半分钟 (30秒)
                if time.time() - self.listening_start_time > 30:
                    logger.info("长时间未检测到语音，自动返回待机状态...")
                    self.dispatcher.publish(create_event(
                        EventType.USER_DEACTIVATE,
                        source="engine"
                    ))
                    # 重置时间，防止下次误判
                    delattr(self, 'listening_start_time')
                    return

                # logger.info("正在录音...") # 避免刷屏，可以注释或改为 debug
                
                # 模拟 VAD，使用较短的 timeout 避免长时间阻塞
                # 如果用户没说话，抛出 WaitTimeoutError，被捕获后重新触发 STT_ERROR
                record_audio(self.temp_audio_input, timeout=5, phrase_time_limit=5)
                
                if os.path.exists(self.temp_audio_input):
                    # 检测到有效语音，重置计时器
                    if hasattr(self, 'listening_start_time'):
                        delattr(self, 'listening_start_time')
                    
                    self.dispatcher.publish(create_event(
                        EventType.VAD_START,
                        source="engine"
                    ))
            except Exception as e:
                # 屏蔽超时错误日志，让它安静地循环
                if "timeout" not in str(e).lower() and "failed after all retries" not in str(e).lower():
                    logger.error(f"录音异常: {e}")
                
                # 发送事件让状态机重新回到 LISTENING
                self.dispatcher.publish(create_event(
                    EventType.STT_ERROR,
                    source="engine"
                ))
        
        threading.Thread(target=_record_task, daemon=True).start()

    def _handle_stt_error(self, event: Event):
        """处理识别/录音错误事件"""
        self.state_machine.process_event(event)

    def _handle_stt_start(self, event: Event):
        """开始语音转文字"""
        def _stt_task():
            logger.info("正在识别语音...")
            text = self.stt_client.recognize(self.temp_audio_input)
            if text:
                logger.info(f"识别结果: {text}")
                self.dispatcher.publish(create_event(
                    EventType.STT_COMPLETE,
                    source="engine",
                    data={"text": text}
                ))
            else:
                logger.warning("未能识别语音")
                self.dispatcher.publish(create_event(
                    EventType.STT_ERROR,
                    source="engine"
                ))
        
        threading.Thread(target=_stt_task, daemon=True).start()

    def _handle_user_input_received(self, event: Event):
        """处理接收到的用户文本"""
        text = event.data.get("text")
        def _llm_task():
            logger.info(f"正在请求 LLM: {text}")
            reply = self.llm_client.chat(text)
            logger.info(f"LLM 回复: {reply}")
            self.dispatcher.publish(create_event(
                EventType.LLM_RESPONSE_RECEIVED,
                source="engine",
                data={"text": reply}
            ))
        
        threading.Thread(target=_llm_task, daemon=True).start()

    def _handle_tts_start(self, event: Event):
        """开始文字转语音并播放"""
        text = event.data.get("text") if event.data else None
        if not text and self.state_machine.current_state == AssistantState.SPEAKING:
            return

        def _tts_play_task():
            logger.info("正在合成语音并播放...")
            logger.info(f"TTS mode: {self.tts_client.mode}, base_url: {getattr(self.tts_client, 'base_url', 'N/A')}")
            
            output_path = self.temp_audio_output if self.tts_client.mode == "server" else "temp_output.wav"
            
            try:
                self.tts_client.synthesize(text, output_path)
                logger.info(f"TTS synthesize completed, playing: {output_path}")
                self.dispatcher.publish(create_event(
                    EventType.AUDIO_OUTPUT_START,
                    source="engine"
                ))
                self.player.play(output_path)
                self.dispatcher.publish(create_event(
                    EventType.AUDIO_OUTPUT_END,
                    source="engine"
                ))
            except Exception as e:
                logger.error(f"TTS 或播放错误: {e}")
                self.dispatcher.publish(create_event(
                    EventType.AUDIO_OUTPUT_END,
                    source="engine"
                ))
        
        threading.Thread(target=_tts_play_task, daemon=True).start()

    def _handle_stt_complete(self, event: Event):
        """处理语音识别完成事件"""
        self.state_machine.process_event(event)
        # 发布用户输入接收事件，触发 LLM
        self.dispatcher.publish(create_event(
            EventType.USER_INPUT_RECEIVED,
            source="engine",
            data={"text": event.data.get("text")}
        ))
    
    def _handle_llm_response(self, event: Event):
        """处理大模型响应事件"""
        import re
        text = event.data.get("text", "") if event.data else ""

        if re.search(r'[\[【]\s*休息\s*[\]】]', text):
            self.pending_music = None
            self.state_machine.set_state(AssistantState.IDLE)
            self.dispatcher.publish(create_event(
                EventType.USER_DEACTIVATE,
                source="engine",
                data={"reason": "rest"}
            ))
            return

        self.state_machine.process_event(event)
        
        # 解析是否包含音乐播放指令 [PLAY_MUSIC:歌名]
        match = re.search(r'[\[【]\s*PLAY_MUSIC\s*:\s*(.*?)\s*[\]】]', text)
        if match:
            song_name = match.group(1).strip()
            text = re.sub(r'[\[【]\s*PLAY_MUSIC\s*:\s*.*?\s*[\]】]', '', text).strip()
            self.pending_music = song_name
        else:
            self.pending_music = None

        # 触发 TTS
        if text:
            self.dispatcher.publish(create_event(
                EventType.TTS_START,
                source="engine",
                data={"text": text}
            ))
        elif self.pending_music:
            # 如果没有文本直接开始播放音乐
            self.dispatcher.publish(create_event(
                EventType.MUSIC_START,
                source="engine",
                data={"song": self.pending_music}
            ))
            self.pending_music = None
    
    def _handle_audio_output_end(self, event: Event):
        """处理音频输出结束事件"""
        # 如果有待播放的音乐，触发 MUSIC_START
        if getattr(self, 'pending_music', None):
            song = self.pending_music
            self.pending_music = None
            self.dispatcher.publish(create_event(
                EventType.MUSIC_START,
                source="engine",
                data={"song": song}
            ))
        else:
            self.state_machine.process_event(event)

    def _handle_music_start(self, event: Event):
        """处理开始播放音乐"""
        self.state_machine.process_event(event)
        song_name = event.data.get("song")
        # 查找音乐文件（支持当前目录的 mp3）
        song_path = f"{song_name}.mp3"
        
        def _play_music_task():
            if os.path.exists(song_path):
                logger.info(f"开始播放音乐: {song_path}")
                try:
                    self.dispatcher.publish(create_event(
                        EventType.AUDIO_OUTPUT_START,
                        source="engine",
                        data={"song": song_name}
                    ))
                    self.player.play(song_path)
                except Exception as e:
                    logger.error(f"播放音乐失败: {e}")
            else:
                logger.warning(f"未找到音乐文件: {song_path}")
            
            # 播放结束或失败，触发 MUSIC_END
            self.dispatcher.publish(create_event(
                EventType.MUSIC_END,
                source="engine"
            ))
            
        threading.Thread(target=_play_music_task, daemon=True).start()

    def _handle_music_end(self, event: Event):
        """处理音乐播放结束"""
        self.state_machine.process_event(event)
    
    def _on_enter_idle(self):
        """进入空闲状态"""
        logger.info("--- 状态切换: IDLE ---")
        if hasattr(self, 'listening_start_time'):
            delattr(self, 'listening_start_time')
        
        # 在 IDLE 状态下启动轻量级的唤醒词监听
        def _wake_word_task():
            try:
                # logger.info("正在监听唤醒词...")
                # 使用较短的超时时间，不断循环监听唤醒词
                record_audio(self.temp_audio_input, timeout=3, phrase_time_limit=3)
                
                if os.path.exists(self.temp_audio_input):
                    # 识别是否包含唤醒词 (这里使用现有的 STT 替代专用的唤醒词模型，仅作演示)
                    text = self.stt_client.recognize(self.temp_audio_input)
                    if text and ("芙宁娜" in text or "唤醒" in text):
                        logger.info(f"检测到唤醒词: {text}")
                        self.dispatcher.publish(create_event(
                            EventType.USER_ACTIVATE,
                            source="engine"
                        ))
                    else:
                        # 没检测到唤醒词，如果还在 IDLE 状态，继续监听
                        if self.state_machine.current_state == AssistantState.IDLE:
                            self._on_enter_idle()
            except Exception as e:
                # 忽略超时错误，继续循环
                if self.state_machine.current_state == AssistantState.IDLE:
                    self._on_enter_idle()
                    
        # 只有在确实是 IDLE 状态时才启动监听
        if self.state_machine.current_state == AssistantState.IDLE:
            threading.Thread(target=_wake_word_task, daemon=True).start()
    
    def _on_enter_listening(self):
        """进入监听状态"""
        logger.info("--- 状态切换: LISTENING ---")
        self.dispatcher.publish(create_event(
            EventType.AUDIO_INPUT_START,
            source="state_machine"
        ))
    
    def _on_enter_recognizing(self):
        """进入语音识别状态"""
        logger.info("--- 状态切换: RECOGNIZING ---")
        self.dispatcher.publish(create_event(
            EventType.STT_START,
            source="state_machine"
        ))
    
    def _on_enter_processing(self):
        """进入处理状态"""
        logger.info("--- 状态切换: PROCESSING ---")
    
    def _on_enter_speaking(self):
        """进入说话状态"""
        logger.info("--- 状态切换: SPEAKING ---")
        
        # 在说话状态下启动打断监听任务
        def _interrupt_listen_task():
            try:
                # 缩短超时和录音时间，实现快速响应打断
                record_audio(self.temp_audio_input, timeout=2, phrase_time_limit=3)
                if os.path.exists(self.temp_audio_input) and self.state_machine.current_state == AssistantState.SPEAKING:
                    text = self.stt_client.recognize(self.temp_audio_input)
                    if text and any(word in text for word in ["停下", "闭嘴", "别说了", "等一下", "打断"]):
                        logger.info(f"检测到语音打断词: {text}")
                        # 触发打断事件
                        self.dispatcher.publish(create_event(
                            EventType.USER_INTERRUPT,
                            source="engine",
                            data={"reason": "voice_interrupt", "text": text}
                        ))
                    elif self.state_machine.current_state == AssistantState.SPEAKING:
                        # 没听到打断词，如果还在说话，继续监听
                        self._on_enter_speaking()
            except Exception:
                # 忽略超时，如果还在说话状态，继续循环监听
                if self.state_machine.current_state == AssistantState.SPEAKING:
                    self._on_enter_speaking()
                    
        # 只有在确实是 SPEAKING 状态时才启动打断监听
        if self.state_machine.current_state == AssistantState.SPEAKING:
            threading.Thread(target=_interrupt_listen_task, daemon=True).start()

    def _on_enter_singing(self):
        """进入唱歌状态"""
        logger.info("--- 状态切换: SINGING ---")
        
        # 在唱歌状态下启动打断监听任务
        def _interrupt_listen_task():
            try:
                # 缩短超时和录音时间，实现快速响应打断
                record_audio(self.temp_audio_input, timeout=2, phrase_time_limit=3)
                if os.path.exists(self.temp_audio_input) and self.state_machine.current_state == AssistantState.SINGING:
                    text = self.stt_client.recognize(self.temp_audio_input)
                    if text and any(word in text for word in ["停下", "闭嘴", "别说了", "等一下", "打断", "别唱了"]):
                        logger.info(f"检测到语音打断词: {text}")
                        # 触发打断事件
                        self.dispatcher.publish(create_event(
                            EventType.USER_INTERRUPT,
                            source="engine",
                            data={"reason": "voice_interrupt", "text": text}
                        ))
                    elif self.state_machine.current_state == AssistantState.SINGING:
                        # 没听到打断词，如果还在唱歌，继续监听
                        self._on_enter_singing()
            except Exception:
                # 忽略超时，如果还在唱歌状态，继续循环监听
                if self.state_machine.current_state == AssistantState.SINGING:
                    self._on_enter_singing()
                    
        # 只有在确实是 SINGING 状态时才启动打断监听
        if self.state_machine.current_state == AssistantState.SINGING:
            threading.Thread(target=_interrupt_listen_task, daemon=True).start()

    def _on_enter_error(self):
        """进入错误状态"""
        logger.info("--- 状态切换: ERROR ---")
    
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
