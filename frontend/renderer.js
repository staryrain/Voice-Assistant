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
  error: "../funingna_skin/error.gif"
};

// 当前状态
let currentState = 'idle';
let idleInterval = null;

const petImg = document.getElementById("pet");

// 状态设置函数
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

// ================= WebSocket 通信 =================
function connectWebSocket() {
  const ws = new WebSocket("ws://127.0.0.1:8000/ws");

  ws.onopen = () => {
    console.log("WebSocket connected to backend");
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      console.log("Received event:", msg);
      
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
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
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