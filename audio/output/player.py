import pygame
import os
import time
import logging

# 配置日志
logger = logging.getLogger(__name__)

class AudioPlayer:
    def __init__(self):
        try:
            pygame.mixer.init()
            logger.info("Audio player initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize audio player: {e}")

    def play(self, file_path: str):
        """
        播放指定路径的音频文件。
        支持 mp3, wav 等 pygame 支持的格式。
        """
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return

        try:
            logger.info(f"Playing audio: {file_path}")
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # 阻塞直到播放结束
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            logger.info("Audio playback finished.")
        except Exception as e:
            logger.error(f"Error playing audio {file_path}: {e}")
        finally:
            # 确保释放资源，虽然 pygame.mixer.music.stop() 不是必须的，但对于长运行程序是好习惯
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except AttributeError:
                # 兼容旧版本 pygame
                pass
            # 注意：不要调用 pygame.quit()，因为这会关闭整个 pygame 模块，如果后续还要播放则需要重新 init

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    player = AudioPlayer()
    # 假设有一个测试文件，这里仅作为示例
    # player.play("test.mp3")
