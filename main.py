#!/usr/bin/env python3
"""
桌面语音助手主入口文件
"""

import sys
import os
import logging
import re
from pathlib import Path
import time

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# from core.engine import AssistantEngine
# from ui.app import MainWindow
from utils.logger import setup_logger
# from config.settings import load_settings

from audio.input.microphone import record_audio
from audio.input.stt import STTClient
from audio.output.tts import TTSClient
from audio.output.player import AudioPlayer
from llm.adapter import LLMClient

def main():
    """主函数"""
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("启动桌面语音助手 (CLI 模式)...")

    # 初始化各模块
    try:
        stt_client = STTClient()
        llm_client = LLMClient()
        tts_client = TTSClient()
        player = AudioPlayer()
        
        logger.info("所有模块初始化完成。")
        print("\n=== 语音助手已就绪 ===")
        
        temp_audio_input = "temp_input.wav"
        temp_audio_output = "temp_output.mp3"
        wake_word = "芙宁娜"
        wake_timeout_seconds = 60
        wake_active_until = 0.0
        wake_response_audio = "test_wakeresponse.mp3"

        while True:
            print("\n请选择沟通方式:")
            print("1. 语音沟通")
            print("2. 文字沟通")
            print("输入 'q' 退出程序")
            
            try:
                mode = input("请输入选项 (1/2): ").strip()
            except EOFError:
                break

            if mode.lower() == 'q':
                break
            
            if mode not in ['1', '2']:
                print("无效选项，请重新选择。")
                continue

            mode_name = "语音" if mode == '1' else "文字"
            print(f"\n已进入{mode_name}沟通模式。")
            print("输入/说出 '重选' 返回选择界面，输入/说出 '退出' 结束程序")
            if mode == '1':
                print(f"请开始说话 (先说出“{wake_word}”唤醒；唤醒后 1 分钟内无需重复唤醒)")

            while True:
                try:
                    text = ""
                    
                    if mode == '1': # 语音模式
                        # 1. 录音
                        print("\n[1/5] 正在录音... (请说话)")
                        # 这里设置简单的固定时长录音作为演示
                        # 实际应用中应该使用 VAD 检测语音结束
                        record_audio(temp_audio_input, timeout=5, phrase_time_limit=5)
                        
                        if not os.path.exists(temp_audio_input):
                            logger.warning("录音文件未生成，重试...")
                            continue

                        # 2. 语音转文字 (STT)
                        print("[2/5] 正在识别...")
                        text = stt_client.recognize(temp_audio_input)
                        print(f"识别结果: {text}")

                        if not text:
                            logger.info("未识别到语音，继续监听...")
                            continue
                    
                    else: # 文字模式
                        try:
                            text = input("\n[文字模式] 请输入: ").strip()
                        except EOFError:
                            break
                        
                        if not text:
                            continue

                    # 通用指令处理
                    if "重选" in text or "reselect" in text.lower():
                        print("返回模式选择界面...")
                        break
                    
                    if "退出" in text or "再见" in text or "exit" in text.lower():
                        print("收到退出指令，程序结束。")
                        return # 退出整个程序

                    if mode == '1':
                        now = time.time()
                        wake_active = now < wake_active_until

                        if not wake_active:
                            if wake_word not in text:
                                logger.info("未检测到唤醒词，忽略本次语音输入")
                                continue

                            wake_active_until = now + wake_timeout_seconds
                            if os.path.exists(wake_response_audio):
                                player.play(wake_response_audio)

                            text = text.replace(wake_word, "", 1)
                            text = re.sub(r'^[\s,，。.!！？:：;；\-]+', '', text).strip()
                            if not text:
                                time.sleep(0.2)
                                continue
                        else:
                            wake_active_until = now + wake_timeout_seconds
                            text = text.strip()
                            if wake_word in text:
                                text = text.replace(wake_word, "", 1)
                                text = re.sub(r'^[\s,，。.!！？:：;；\-]+', '', text).strip()
                            if not text:
                                continue

                    # 3. 大模型对话 (LLM)
                    print("[3/5] 正在思考...")
                    reply = llm_client.chat(text)
                    print(f"AI 回复: {reply}")

                    # --- 音乐播放逻辑开始 ---
                    # 匹配 [PLAY_MUSIC:歌名]，允许前后有空白字符
                    music_tag_match = re.search(r'\[\s*PLAY_MUSIC\s*:\s*(.*?)\s*\]', reply)
                    music_to_play = None
                    
                    if music_tag_match:
                        music_name = music_tag_match.group(1).strip()
                        # 如果歌名为非空才处理
                        if music_name:
                            # 清理可能带有的书名号
                            music_name = music_name.strip('《》')
                            # 移除回复中的提示词，不让 TTS 读出来
                            clean_reply = re.sub(r'\[\s*PLAY_MUSIC\s*:.*?\]', '', reply).strip()
                            
                            # 查找对应的音频文件
                            potential_files = [
                                f"{music_name}.mp3",
                                f"{music_name}.wav",
                                music_name if music_name.endswith(('.mp3', '.wav')) else None
                            ]
                            
                            for pf in potential_files:
                                if pf and os.path.exists(pf):
                                    music_to_play = pf
                                    break
                            
                            if music_to_play:
                                logger.info(f"检测到音乐播放指令: {music_name}, 将在语音播报后播放 {music_to_play}")
                            else:
                                logger.warning(f"检测到音乐播放指令: {music_name}, 但未找到对应音频文件")
                        else:
                            # 如果是空歌名标记，直接移除不处理
                            clean_reply = re.sub(r'\[\s*PLAY_MUSIC\s*:.*?\]', '', reply).strip()
                    else:
                        clean_reply = reply
                    # --- 音乐播放逻辑结束 ---

                    # 4. 文字转语音 (TTS)
                    print("[4/5] 正在合成语音...")
                    
                    # 尝试删除旧的音频文件，防止占用
                    if os.path.exists(temp_audio_output):
                        try:
                            os.remove(temp_audio_output)
                        except Exception as e:
                            logger.warning(f"无法删除旧音频文件: {e}")

                    tts_client.synthesize(clean_reply, temp_audio_output)

                    # 5. 播放音频
                    print("[5/5] 正在播放回复语音...")
                    player.play(temp_audio_output)
                    
                    # 如果有音乐指令，播报完后播放音乐
                    if music_to_play:
                        print(f"[*] 正在播放歌曲: {music_name}")
                        player.play(music_to_play)
                    
                    # 简单的延时，避免循环过快
                    time.sleep(1)

                except KeyboardInterrupt:
                    print("\n返回模式选择界面...")
                    break
                except Exception as e:
                    logger.error(f"处理循环发生错误: {e}")
                    time.sleep(2) # 出错后等待一会再重试

    except Exception as e:
        logger.exception(f"应用启动失败: {e}")
        sys.exit(1)
    finally:
        # 清理临时文件
        if os.path.exists(temp_audio_input):
            os.remove(temp_audio_input)
        if os.path.exists(temp_audio_output):
            os.remove(temp_audio_output)

if __name__ == "__main__":
    main()
