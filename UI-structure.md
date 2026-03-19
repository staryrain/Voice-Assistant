

# 🧠 一、整体目标效果（先让你有画面感）

你的桌宠运行后，大概是这样：

---

## 🎬 桌面效果

* 屏幕上有一个**透明背景的角色（GIF）**
* 没有窗口边框，就像“贴在桌面上”
* 可以：

  * 🖱️ 拖动
  * 🖱️ 点击互动
  * 🔊 根据语音自动变化状态

---

## 🎭 状态表现（核心体验）

| 状态                      | UI表现            |
| ----------------------- | --------------- |
| IDLE                    | 角色发呆/待机（偶尔小动作）  |
| LISTENING               | 侧耳倾听 / 有“在听”的感觉 |
| RECOGNIZING / PROCESSING              | 思考（比如点头/转圈/冒问号） |
| SPEAKING                | 张嘴说话（循环动画）      |
| ERROR                   | 困惑 / 生气 / ❗表情   |

---

👉 用户体验会是：

```text
你说话 → 角色“侧耳听” → “思考” → “开口说话”
```

👉 这一步你已经从“工具”变成“角色”了 ⭐

---

# 🏗️ 二、Electron架构设计（核心）

---

## 🧩 总体结构

```text
Electron 主进程（main.js）
   ↓
渲染进程（UI界面）
   ↓
动画控制器（Animation Controller）
   ↓
状态（来自后端语音系统）
```

---

## 🔌 和你后端的关系

你现在有语音助手（Python）：

👉 建议用：

```text
WebSocket 
```

通信：

```json
{ "state": "listening" }
```

---

# 🎯 三、核心模块设计（重点）

---

# 1️⃣ 主窗口（透明桌宠）

### Electron配置：

```javascript
const win = new BrowserWindow({
  width: 400,
  height: 400,
  frame: false,        // 无边框
  transparent: true,   // 透明
  alwaysOnTop: true,   // 置顶
  resizable: false,
  hasShadow: false,
  webPreferences: {
    nodeIntegration: true,
    contextIsolation: false
  }
})
```

---

👉 效果：

* 没有窗口边框
* 角色“悬浮在桌面上”

---

# 2️⃣ UI结构（前端页面）

```html
<body>
  <img id="pet" src="idle.gif" />
</body>
```

---

### CSS（关键）

```css
body {
  margin: 0;
  background: transparent;
  overflow: hidden;
}

#pet {
  width: 100%;
  -webkit-user-drag: none;
}
```

---

---

# 3️⃣ 动画控制器（核心逻辑）

👉 你最重要的一层！

---

```javascript
const animations = {
  idle: "idle.gif",
  listening: "listen.gif",
  recognizing: "thinking.gif",
  processing: "thinking.gif",
  speaking: "talk.gif",
  error: "error.gif"
}

function setState(state) {
  const pet = document.getElementById("pet")
  pet.src = animations[state] || animations["idle"]
}
```

---

👉 以后你所有状态变化：
**只调用 setState()**

---

---

# 4️⃣ 状态通信（和后端联动）

---

## 🟢 方式1：WebSocket（推荐）

```javascript
const ws = new WebSocket("ws://localhost:12345")

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  setState(data.state)
}
```

---

## 🟡 方式2：简单HTTP轮询（不推荐但能用）

---

---

# 5️⃣ 拖动桌宠（非常关键）

```javascript
let isDragging = false

document.addEventListener("mousedown", () => {
  isDragging = true
})

document.addEventListener("mouseup", () => {
  isDragging = false
})

document.addEventListener("mousemove", (e) => {
  if (isDragging) {
    window.moveTo(e.screenX, e.screenY)
  }
})
```

---

👉 效果：

* 角色可以被拖着走

---

# 🎨 四、动画设计建议（非常关键）

---

## 🎯 你的状态 → 动画映射（推荐优化版）

```javascript
const animations = {
  idle: ["idle1.gif", "idle2.gif"，idle3，idle4,idle5], // 随机
  listening: "listen.gif",
  recognizing: "thinking.gif",
  processing: "thinking.gif",
  speaking: "talk.gif",
  error: "error.gif"
}
```

---



# 🔊 五、语音联动（让它“活”起来）

---

## 🎯 SPEAKING 状态增强

简单版：

* 说话 → 播放 talk.gif



---

# 🎭 六、完整交互流程（你最终效果）

---

```text
IDLE（发呆）

→ 用户说话

LISTENING（侧耳）

→ 语音识别

RECOGNIZING（思考）

→ LLM处理

PROCESSING（思考）

→ 生成回复

SPEAKING（说话）

→ 播放结束

回到 IDLE
```

---

👉 这是一个**完整的角色行为闭环** ⭐

---

# 🧨 七、可以加的高级功能（下一步）


## 🔥 3️⃣ 气泡UI（推荐）

在角色旁边加：

```text
💬 “你好呀~”
```

---

---

