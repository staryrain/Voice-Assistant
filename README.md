# 桌面语音助手

一个基于Python的桌面语音助手应用，支持语音识别、自然语言处理和文本转语音功能。

## 功能特点

- 🎙️ 实时语音识别（STT）
- 💬 智能对话交互
- 📢 文本转语音（TTS）
- 📝 对话历史记录
- 🎨 友好的桌面界面
- 🔧 可配置的模型和参数

## 安装步骤

1. 克隆项目
   ```bash
   git clone <repository-url>
   cd Voice-Assistant
   ```

2. 激活虚拟环境
   ```bash
   # Windows
   venv\Scripts\activate
   
  

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. 运行应用
   ```bash
   python main.py
   ```

## 项目结构

```
.
├── config/              # 配置文件
│   ├── settings.yaml    # 模型、音频、阈值配置
│   └── prompts.yaml     # 人设 / system prompt
├── core/               # 核心功能
│   ├── engine.py        # 事件循环引擎
│   ├── state_machine.py # 状态机
│   ├── events.py        # 事件定义
│   └── dispatcher.py    # 事件分发器
├── audio/              # 音频处理
│   ├── input/           # 音频输入
│   │   ├── microphone.py # 麦克风采集
│   │   ├── vad.py        # 语音活动检测
│   │   └── stt.py        # 语音识别
│   └── output/          # 音频输出
│       ├── tts.py        # 文本转语音
│       └── player.py     # 音频播放
├── llm/                # 大语言模型
│   └── adapter.py       # API 封装
├── memory/             # 记忆管理
│   ├── short_term.py    # 对话上下文
│   └── store.py         # 持久化存储
├── ui/                 # 用户界面
│   ├── app.py           # 主窗口
│   └── signals.py       # UI-核心信号
├── utils/              # 工具函数
│   ├── logger.py        # 日志记录
│   ├── sentence_split.py # 句子切分
│   └── time_utils.py    # 时间工具
├── tests/              # 测试文件
│   ├── test_state_machine.py
│   └── test_events.py
├── main.py             # 程序入口
├── requirements.txt    # 依赖列表
└── README.md           # 项目说明
```

## 配置说明

在 `config/settings.yaml` 中可以配置：
- 语音识别模型
- 文本转语音参数
- 音频设备设置
- 阈值配置

在 `config/prompts.yaml` 中可以配置：
- 助手的人设
- System prompt

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
