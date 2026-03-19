# 语音助手核心模块接口文档

本文档描述了语音助手中音频输入、输出、语音识别、语音合成及大模型适配器的接口定义。

## 1. 麦克风录音 (Audio Input)

**文件路径**: `audio/input/microphone.py`

### `record_audio(file_path, timeout=10, phrase_time_limit=None, retries=3, energy_threshold=2000, pause_threshold=1, phrase_threshold=0.1, dynamic_energy_threshold=True, calibration_duration=1)`

录制音频并保存到指定文件。

*   **参数**:
    *   `file_path` (str): 音频文件保存路径 (支持 .wav, .mp3)。
    *   `timeout` (int): 等待语音开始的最大秒数 (默认 10)。
    *   `phrase_time_limit` (int): 单次语音录制的最大秒数 (默认 None，即不限制)。
    *   `retries` (int): 录音失败重试次数 (默认 3)。
    *   `energy_threshold` (int): 能量阈值，用于静音检测 (默认 2000)。
    *   `pause_threshold` (float): 静音检测阈值，多少秒的静音被视为短语结束 (默认 1)。
    *   `phrase_threshold` (float): 短语最小长度阈值 (秒) (默认 0.1)。
    *   `dynamic_energy_threshold` (bool): 是否启用动态能量阈值调整 (默认 True)。
    *   `calibration_duration` (float): 环境噪声校准时长 (秒) (默认 1)。
*   **返回**: 无 (录制成功则文件被创建，失败抛出异常)。
*   **异常**: `WaitTimeoutError` (超时), `Exception` (录音失败)。

---

## 2. 语音识别 (STT - Speech to Text)

**文件路径**: `audio/input/stt.py`

### 类 `STTClient`

封装了语音识别服务的客户端，使用字节跳动火山引擎 ASR 服务。

#### `__init__(self)`

初始化客户端，配置 ASR 服务的认证信息和连接参数。

*   **说明**: 内部使用默认的 app_key、access_key 和 WebSocket URL。

#### `recognize(self, file_path: str) -> str`

识别指定音频文件中的文本（同步阻塞方法）。

*   **参数**:
    *   `file_path` (str): 待识别的音频文件路径。
*   **返回**: 识别出的文本字符串。如果识别失败或无内容，返回空字符串。
*   **说明**: 内部使用异步方法实现，音频会被转换为 16kHz PCM 格式进行识别。

---

## 3. 大模型适配器 (LLM Adapter)

**文件路径**: `llm/adapter.py`

### 类 `LLMClient`

封装了与大语言模型 (LLM) 的交互逻辑，使用火山引擎豆包大模型，包含人设管理。

#### `__init__(self)`

初始化客户端，配置 OpenAI 兼容 API 并加载人设配置。

*   **说明**: 从 `persona.txt` 文件读取人设配置，API Key 从环境变量 `ARK_API_KEY` 读取。

#### `chat(self, user_input: str) -> str`

发送用户输入并获取 AI 回复。

*   **参数**:
    *   `user_input` (str): 用户输入的文本。
*   **返回**: AI 的回复文本。
*   **说明**: 该方法会自动维护对话历史 (Context)，使用豆包-1.5-pro-32k 模型。

#### `reset_history(self)`

重置对话历史，恢复到初始人设状态。

*   **说明**: 重新加载 persona.txt 文件，清空之前的对话记录。

---

## 4. 语音合成 (TTS - Text to Speech)

**文件路径**: `audio/output/tts.py`

### 类 `TTSClient`

封装了语音合成服务的客户端，使用字节跳动火山引擎 TTS 服务。

#### `__init__(self, appid=DEFAULT_APPID, token=DEFAULT_TOKEN, cluster=DEFAULT_CLUSTER)`

初始化客户端，配置 TTS 服务的认证信息。

#### `synthesize(self, text: str, output_path: str = "output.mp3", voice_type=DEFAULT_VOICE_TYPE) -> str`

将文本合成为语音并保存到文件（同步阻塞方法）。

*   **参数**:
    *   `text` (str): 待合成的文本。
    *   `output_path` (str): 输出音频文件的路径 (默认 "output.mp3"，通常为 .mp3)。
    *   `voice_type` (str): 音色 ID (可选，默认为 "S_FwdJnJNN1")。
*   **返回**: 输出文件的路径。
*   **说明**: 内部使用异步 WebSocket 连接实现，返回 MP3 格式的音频文件。

---

## 5. 音频播放 (Audio Player)

**文件路径**: `audio/output/player.py`

### 类 `AudioPlayer`

封装了音频播放功能，基于 pygame mixer。

#### `__init__(self)`

初始化播放器 (pygame mixer)。

*   **说明**: 初始化 pygame.mixer 模块，用于音频播放。

#### `play(self, file_path: str)`

播放指定路径的音频文件（阻塞直到播放结束）。

*   **参数**:
    *   `file_path` (str): 音频文件路径 (支持 mp3, wav 等 pygame 支持的格式)。
*   **返回**: 无。
*   **说明**: 方法会阻塞直到音频播放完成，播放完成后自动释放资源。
