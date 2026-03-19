为了保证 UI 不卡顿，建议将程序分为 **UI 界面层**、**核心逻辑层** 和 **外部服务层**。

### 1. 架构图解

### 2. 模块化设计方案

#### **A. 输入感知层 (Input Sensing)**

* **语音监听 (VAD):** 使用 Voice Activity Detection（如 Silero VAD）来判断你是否在说话，避免持续上传静音数据。
* **唤醒词检测 (Wake-word):** 参照“小爱同学”那种效果，可以用 Porcupine 或 Snowboy 进行本地离线唤醒词检测。
[Idle]
  └── Wake-word 检测
        └── 切换到 Listening 状态
               └── VAD + STT


#### **B. 核心中枢层 (Core Engine - 异步处理中心)**

这是软件的“交感神经”，建议使用 `asyncio` (Python) 或事件循环机制：

* **状态机 (State Machine):** 管理助手的状态（待机、倾听中、思考中、说话中）。
* **消息分发器:** 将识别到的文本分发给大模型，同时处理可能的中断指令（比如你突然说“别说了”）。

🔥 强烈建议加的一层：事件总线 / 命令队列

不要让模块直接互相调用，而是通过事件：

* **EVENT_USER_SPEECH_END**
* **EVENT_LLM_TOKEN**
* **EVENT_INTERRUPT**
* **EVENT_TTS_FINISHED**


推荐结构：

@dataclass
class Event:
  {  
    type: EventType
    payload: Any
  }



#### **C. 外部集成层 (Integration)**

* **大模型适配器:** 封装你的 API 调用逻辑，支持流式传输（Streaming），这样助手可以在生成第一句话时就开始朗读，减少等待感。
* **记忆模块 (Memory):** 使用简单的 JSON 或本地数据库（SQLite）存储短期对话上下文。

---

## 3. 技术栈推荐方案

| 维度 | 推荐工具 | 理由 |
| --- | --- | --- |
| **GUI 框架** | **PyQt6** | PyQt 性能好，方便调用 Python 库。 |
| **异步处理** | **Python `asyncio**` | 语音处理和 API 调用都是 I/O 密集型，异步是必须的。 |
| **音频流处理** | **PyAudio** / **SoundDevice** | 稳定且支持实时流。 |
| **通信协议** | **WebSocket** | 如果 UI 和后端分离，WebSocket 能实现极低延迟的双向通信。 |

---

## 4. 关键交互流程设计：流式响应 (Streaming)

为了让助手更有“人味”，建议实现**流式交互控制**：

1. **用户说话** \rightarrow VAD 截取音频。
2. **STT (语音转文本)** \rightarrow 实时转换。
3. **LLM (大模型)** \rightarrow 开启 `stream=True`。
4. **TTS (文本转语音)** \rightarrow **关键点：** 不要等 LLM 全部回复完。每当 LLM 生成一个完整的句子（遇到句号/感叹号），立即送入 TTS 生成音频并播放。

---
项目结构：

Voice—Assistant/
│
├── README.md
├── requirements.txt
├── main.py                 # 程序入口
│
├── config/
│   ├── settings.yaml       # 模型、音频、阈值
│   └── prompts.yaml        # 人设 / system prompt
│
├── core/
│   ├── __init__.py
│   │
│   ├── engine.py           # Core Engine（事件循环）
│   ├── state_machine.py    # 状态机定义
│   ├── events.py           # Event 类型定义
│   └── dispatcher.py       # 事件分发器
│
├── audio/
│   ├── __init__.py
│   │
│   ├── input/
│   │   ├── microphone.py   # 麦克风采集
│   │   ├── vad.py          # VAD 封装
│   │   └── stt.py          # STT 适配
│   │
│   └── output/
│       ├── tts.py          # TTS 适配
│       └── player.py       # 音频播放（支持中断）
│
├── llm/
│   ├── __init__.py
│   └── adapter.py          # 大模型 API 封装
│
├── memory/
│   ├── __init__.py
│   ├── short_term.py       # 当前对话上下文
│   └── store.py            # SQLite / JSON
│
├── ui/
│   ├── __init__.py
│   ├── app.py              # PyQt6 主窗口
│   └── signals.py          # UI <-> Core 信号
│
├── utils/
│   ├── logger.py
│   ├── sentence_split.py   # 句子级切分
│   └── time_utils.py
│
└── tests/
    ├── test_state_machine.py
    └── test_events.py
