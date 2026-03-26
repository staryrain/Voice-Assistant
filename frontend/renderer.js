// 动画状态映射表
const animations = {
  idle: [
    "../funingna_skin/idle1.gif",
    "../funingna_skin/idle2.gif",
    "../funingna_skin/idle3.gif",
    "../funingna_skin/idle4.gif",
    "../funingna_skin/idle5.gif"
  ],
  listening: "../funingna_skin/listen.gif",
  recognizing: "../funingna_skin/thinking.gif",
  processing: "../funingna_skin/thinking.gif",
  speaking: "../funingna_skin/talk.gif",
  singing: "../funingna_skin/talk.gif",
  error: "../funingna_skin/error.gif"
};

// 当前状态
let currentState = 'idle';
let idleInterval = null;

const petImg = document.getElementById("pet");
let lastBackendState = null;
let lastEventType = null;

function backendStateToAnimState(state) {
  switch (state) {
    case "idle":
      return "idle";
    case "listening":
      return "listening";
    case "recognizing":
      return "recognizing";
    case "processing":
      return "processing";
    case "speaking":
      return "speaking";
    case "singing":
      return "singing";
    case "error":
      return "error";
    default:
      return null;
  }
}

function setState(state) {
  if (state === currentState) return; // 状态未改变
  currentState = state;
  
  clearInterval(idleInterval); // 停止随机 idle

  if (state === 'idle') {
    playRandomIdle();
    // 每隔一段时间随机切换闲置动画
    idleInterval = setInterval(playRandomIdle, 5000 + Math.random() * 5000);
  } else {
    petImg.src = animations[state] || animations["idle"][0];
  }
}

// 播放随机的 Idle 动画
function playRandomIdle() {
  const idleList = animations["idle"];
  const randomIndex = Math.floor(Math.random() * idleList.length);
  petImg.src = idleList[randomIndex];
}

// 初始化状态
setState('idle');

let isTextMode = false;
let globalWs = null; // 用于在其他地方发送消息

// ================= WebSocket 通信 =================
function connectWebSocket() {
  const ws = new WebSocket("ws://127.0.0.1:8000/ws");
  globalWs = ws;

  ws.onopen = () => {
    console.log("WebSocket connected to backend");
    lastEventType = "ws_open";
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      console.log("Received event:", msg);
      lastEventType = msg.type ?? null;
      lastBackendState = msg.state ?? null;

      // 如果在文本模式下收到用户输入（可能是语音识别结果）或大模型回复
      if (isTextMode) {
        if (msg.type === "user_input_received") {
          addMessage(msg.data.text, 'user');
        } else if (msg.type === "llm_response_received") {
          addMessage(msg.data.text, 'llm');
        }
      }

      const animState = backendStateToAnimState(lastBackendState);
      if (animState) {
        setState(animState);
        return;
      }
      
      // 根据后端的事件类型映射到前端的动画状态
      switch (msg.type) {
        case "system_start":
          setState("idle");
          break;
        case "audio_input_start":
        case "vad_start":
          setState("listening");
          break;
        case "vad_end":
        case "stt_start":
          setState("recognizing");
          break;
        case "user_input_received":
        case "llm_response_received":
        case "tts_start":
          setState("processing");
          break;
        case "audio_output_start":
        case "music_start":
          setState("speaking");
          break;
        case "audio_output_end":
        case "music_end":
          setState("idle");
          break;
        case "error":
          setState("error");
          setTimeout(() => setState("idle"), 3000); // 3秒后恢复idle
          break;
        default:
          break;
      }

    } catch (err) {
      console.error("Error parsing message:", err);
    }
  };

  ws.onclose = () => {
    console.log("WebSocket disconnected. Reconnecting in 3 seconds...");
    lastEventType = "ws_close";
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
    lastEventType = "ws_error";
  };
}

// 启动 WebSocket
connectWebSocket();

// ================= 窗口拖拽功能 =================
let isDragging = false;
let mouseOffsetX = 0;
let mouseOffsetY = 0;

petImg.addEventListener("mousedown", (e) => {
  isDragging = true;
  // 记录鼠标相对窗口的偏移量
  mouseOffsetX = e.clientX;
  mouseOffsetY = e.clientY;
});

document.addEventListener("mouseup", () => {
  isDragging = false;
});

document.addEventListener("mousemove", (e) => {
  if (isDragging) {
    // electron 的 screen 坐标
    const { screenX, screenY } = e;
    // 移动窗口到鼠标当前屏幕位置减去按下的偏移量
    window.moveTo(screenX - mouseOffsetX, screenY - mouseOffsetY);
  }
});

// 双击可以手动触发一次唤醒（通过 WebSocket 往上发指令的话，需要通过前面建立的 ws 对象）
// 这里作为保留接口
petImg.addEventListener("dblclick", () => {
  // 仅在演示或前端独立测试时使用
  console.log("Pet double-clicked");
});

// ================= 文本模式 UI 逻辑 =================
const { ipcRenderer } = require('electron');

const contextMenu = document.getElementById("context-menu");
const menuTextMode = document.getElementById("menu-text-mode");
const textModeContainer = document.getElementById("text-mode-container");
const closeTextBtn = document.getElementById("close-text-btn");
const chatMessages = document.getElementById("chat-messages");
const textInput = document.getElementById("text-input");
const sendBtn = document.getElementById("send-btn");

// 显示右键菜单
window.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  if (isTextMode) return; // 文本模式下不显示菜单
  contextMenu.style.display = 'block';
  contextMenu.style.left = e.clientX + 'px';
  contextMenu.style.top = e.clientY + 'px';
});

// 点击其他地方隐藏菜单
window.addEventListener('click', () => {
  contextMenu.style.display = 'none';
});

// 进入文本模式
menuTextMode.addEventListener('click', () => {
  isTextMode = true;
  petImg.style.display = 'none';
  textModeContainer.style.display = 'flex';
  // 调整窗口大小，长宽比1:2
  ipcRenderer.send('resize-window', 350, 700);
  
  if (globalWs && globalWs.readyState === WebSocket.OPEN) {
    globalWs.send(JSON.stringify({
      type: "mode_change",
      data: { mode: "text" }
    }));
  }
});

// 退出文本模式
closeTextBtn.addEventListener('click', () => {
  isTextMode = false;
  petImg.style.display = 'block';
  textModeContainer.style.display = 'none';
  // 恢复原窗口大小
  ipcRenderer.send('resize-window', 400, 400);
  
  if (globalWs && globalWs.readyState === WebSocket.OPEN) {
    globalWs.send(JSON.stringify({
      type: "mode_change",
      data: { mode: "voice" }
    }));
  }
});

// 添加消息到聊天区域
function addMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;
  
  const avatarImg = document.createElement('img');
  avatarImg.className = 'avatar';
  if (sender === 'llm') {
    avatarImg.src = '../funingna_skin/聊天头像.jpg';
  } else {
    // 发送方头像空白
    avatarImg.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; // 透明像素
  }
  
  const bubbleDiv = document.createElement('div');
  bubbleDiv.className = 'bubble';
  bubbleDiv.innerText = text;
  
  msgDiv.appendChild(avatarImg);
  msgDiv.appendChild(bubbleDiv);
  
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 发送消息
function sendMessage() {
  const text = textInput.value.trim();
  if (!text) return;
  
  textInput.value = '';
  
  if (globalWs && globalWs.readyState === WebSocket.OPEN) {
    globalWs.send(JSON.stringify({
      type: "user_text_input",
      data: { text: text }
    }));
  }
}

sendBtn.addEventListener('click', sendMessage);

textInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

