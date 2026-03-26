# 语音助手核心模块接口文档

本文档描述了语音助手的通信协议规范（供前端对接）以及内部核心模块（音频输入/输出、识别、合成及大模型）的接口定义。

---

## 🟢 1. 前端对接通信协议 (WebSocket + HTTP)

为了支持基于 Electron 等前端框架的界面开发，后端服务计划采用 **WebSocket** 与 **HTTP** 的组合方式，提供跨进程、跨语言的通信能力。

### 1.1 架构设计
- **HTTP 接口**: 负责基础配置管理、初始化状态获取等一次性或阻塞式请求。
- **WebSocket 接口**: 负责双向实时流式通信。由于语音助手涉及大量的状态流转（监听、思考、说话）以及实时反馈，WebSocket 是最佳选择。
  - **下行事件 (Backend -> Frontend)**：语音助手状态变更、STT 识别结果、LLM 回复文本推送。
  - **上行指令 (Frontend -> Backend)**：前端发起的控制命令（如主动唤醒、强制打断当前说话）。

### 1.2 WebSocket 实时事件协议 (基于核心状态机)

前端通过 WebSocket 连接到后端本地服务（如 `ws://127.0.0.1:8000/ws`）。数据交互统一采用 JSON 格式：
`{ "type": "event_type", "data": { ... } }`

#### 1.2.1 下行事件（后端发送给前端）
以下事件类型与 Python 后端的 `core/events.py` 中定义的枚举强绑定：

| 事件类型 (type) | 数据负载 (data) | 触发时机与说明 (前端响应建议) |
| :--- | :--- | :--- |
| `system_start` | `{ "status": "ready" }` | 核心引擎初始化完成。**前端动作**：隐藏加载页，进入主界面待机状态。 |
| `audio_input_start` | `{}` | 开始录音。**前端动作**：麦克风图标亮起，提示“正在聆听...”。 |
| `vad_start` | `{}` | VAD 检测到用户开始说话。**前端动作**：展示用户音量波形动画。 |
| `vad_end` | `{}` | VAD 检测到用户停止说话。**前端动作**：停止波形动画，提示“正在识别...”。 |
| `stt_start` | `{}` | 开始将录音进行语音识别。 |
| `user_input_received` | `{ "text": "用户说的话" }` | STT 识别完成。**前端动作**：在界面渲染用户聊天气泡。 |
| `llm_response_received` | `{ "text": "AI的回复" }` | 大模型生成回复完成。**前端动作**：在界面渲染 AI 聊天气泡，提示“正在思考...”。 |
| `tts_start` | `{}` | 开始将 AI 回复转换为语音。 |
| `audio_output_start` | `{}` | 开始播放 AI 的语音回复。**前端动作**：展示 AI 说话动效或 Avatar 动画。 |
| `audio_output_end` | `{}` | 语音回复播放完毕。**前端动作**：恢复到默认待机状态动效。 |
| `error` | `{ "module": "...", "msg": "..." }` | 发生异常。**前端动作**：弹出 Toast 或 Error 提示。 |

#### 1.2.2 上行指令（前端发送给后端）

| 指令类型 (type) | 数据负载 (data) | 触发时机与说明 |
| :--- | :--- | :--- |
| `user_activate` | `{}` | 用户在 UI 点击“唤醒”或“开始说话”按钮，主动触发助手进入监听状态。 |
| `user_interrupt` | `{}` | 用户在 UI 点击“打断”或“停止”按钮，强制打断当前的 TTS 播放或大模型生成。 |

### 1.3 HTTP REST API 规划 (示例)

前端通过 HTTP 接口（如 `http://127.0.0.1:8000/api/...`）进行系统配置读取或修改：

*   **`GET /api/status`**: 获取当前引擎运行状态（Idle, Listening, Thinking, Speaking）。
*   **`GET /api/persona`**: 获取当前助手的系统人设配置内容。
*   **`POST /api/persona`**: 更新助手的系统人设（传入新的 prompt 文本）。
*   **`POST /api/reset_history`**: 清除当前多轮对话的上下文历史，重置对话状态。

---

## 🔵 2. 内部 Python 核心模块 API 参考 (Core Internal API)

以下部分为内部 Python 模块的类与方法定义参考，供后端开发与维护使用。

### 2.1 麦克风录音 (Audio Input)
**文件路径**: `audio/input/microphone.py`

#### `record_audio(file_path, timeout=10, phrase_time_limit=None, retries=3, energy_threshold=2000, pause_threshold=1, phrase_threshold=0.1, dynamic_energy_threshold=True, calibration_duration=1)`
录制音频并保存到指定文件。
*   **参数**:
    *   `file_path` (str): 音频文件保存路径 (支持 .wav, .mp3)。
    *   `timeout` (int): 等待语音开始的最大秒数 (默认 10)。
    *   `energy_threshold` (int): 能量阈值，用于静音检测 (默认 2000)。
*   **异常**: `WaitTimeoutError` (超时), `Exception` (录音失败)。

### 2.2 语音识别 (STT - Speech to Text)
**文件路径**: `audio/input/stt.py`

#### 类 `STTClient`
封装了语音识别服务的客户端，使用火山引擎 ASR 服务。
*   **`recognize(self, file_path: str) -> str`**: 识别指定音频文件中的文本（同步阻塞方法）。返回识别出的文本字符串。

### 2.3 大模型适配器 (LLM Adapter)
**文件路径**: `llm/adapter.py`

#### 类 `LLMClient`
封装了与大语言模型 (LLM) 的交互逻辑，包含人设管理。支持服务器模式（如火山引擎）与本地模式（对接本地 Ollama 服务）。
*   **`chat(self, user_input: str) -> str`**: 发送用户输入并获取 AI 回复。根据 `config/settings.yaml` 中的配置决定请求线上 API 还是本地 Ollama 服务，并自动维护对话历史。
*   **`_chat_server(self, user_input: str) -> str`**: 内部方法，处理与线上 OpenAI 兼容接口的交互。
*   **`_chat_local(self, user_input: str) -> str`**: 内部方法，处理与本地 Ollama 服务（如 `/api/chat`）的交互。
*   **`reset_history(self)`**: 重置对话历史，恢复到初始人设状态。

### 2.4 语音合成 (TTS - Text to Speech)
**文件路径**: `audio/output/tts.py`

#### 类 `TTSClient`
封装了语音合成服务的客户端。支持服务器模式（如火山引擎 TTS 服务）与本地模式（如对接本地 GPT-SoVITS 推理后端）。
*   **`synthesize(self, text: str, output_path: str = "output.mp3", voice_type=...) -> str`**: 将文本合成为语音并保存到文件。根据 `config/settings.yaml` 中的 `tts.mode` 决定使用线上服务还是本地服务。
*   **`_synthesize_server(self, text: str, output_path: str, voice_type: str = None)`**: 内部方法，异步请求线上 WebSocket TTS 接口。
*   **`_synthesize_local(self, text: str, output_path: str)`**: 内部方法，异步请求本地 HTTP TTS 接口（默认使用 `aiohttp`，生成 WAV 格式音频）。

### 2.5 音频播放 (Audio Player)
**文件路径**: `audio/output/player.py`

#### 类 `AudioPlayer`
封装了音频播放功能，基于 pygame mixer。
*   **`play(self, file_path: str)`**: 播放指定路径的音频文件（阻塞直到播放结束）。