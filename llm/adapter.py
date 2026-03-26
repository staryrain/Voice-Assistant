import os
import logging
import yaml
from openai import OpenAI

logger = logging.getLogger(__name__)

def _load_config() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load config: {e}, using empty config")
        return {}

_config = _load_config()

class LLMClient:
    def __init__(self):
        llm_config = _config.get("llm", {})
        self.mode = llm_config.get("mode", "server")
        
        if self.mode == "server":
            server_config = llm_config.get("server", {})
            base_url = server_config.get("base_url", "")
            api_key = server_config.get("api_key", "")
            self.model = server_config.get("model", "")
            self.client = OpenAI(
                base_url=base_url,
                api_key=os.environ.get("ARK_API_KEY", api_key)
            )
        else:
            local_config = llm_config.get("local", {})
            self.base_url = local_config.get("base_url", "http://localhost:11434")
            self.model = local_config.get("model", "gpt-oss:20b")
            
        self.messages = []
        self._load_persona()

    def _load_persona(self):
        # Read the persona from the separate file
        persona_file_path = os.path.join(os.path.dirname(__file__), "persona.txt")
        try:
            with open(persona_file_path, "r", encoding="utf-8") as f:
                personality = f.read()
        except FileNotFoundError:
            logger.warning(f"Persona file not found at {persona_file_path}. Using default persona.")
            personality = "你是一个有帮助的语音助手。"

        self.messages = [
            {"role": "system", "content": personality}
        ]

    def chat(self, user_input: str) -> str:
        """
        发送用户输入并获取 AI 回复
        """
        if self.mode == "server":
            return self._chat_server(user_input)
        else:
            return self._chat_local(user_input)

    def _chat_server(self, user_input: str) -> str:
        try:
            self.messages.append({
                "role": "user",
                "content": user_input
            })

            # Call the API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
            )

            reply = completion.choices[0].message.content
            
            self.messages.append({
                "role": "assistant",
                "content": reply
            })
            
            return reply
        except Exception as e:
            logger.error(f"LLM Chat error: {e}")
            return "抱歉，我现在无法回答。"

    def _chat_local(self, user_input: str) -> str:
        import requests
        try:
            self.messages.append({
                "role": "user",
                "content": user_input
            })

            # 过滤掉 Ollama 不支持的 system 角色，或者确保格式正确
            # Ollama 的 chat 接口有些版本对 system prompt 处理较严格，安全起见我们打印出来
            payload = {
                "model": self.model,
                "messages": self.messages,
                "stream": False
            }

            logger.info(f"Local LLM Requesting: {self.base_url}/api/chat")
            
            # 增加超时时间，本地模型推理可能较慢
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
            
            if response.status_code != 200:
                logger.error(f"Local LLM API error: {response.status_code} - {response.text}")
            
            response.raise_for_status()

            # The response could be in a format that does not have "message" dictionary directly
            response_json = response.json()
            if "message" in response_json and "content" in response_json["message"]:
                reply = response_json["message"]["content"]
            elif "response" in response_json:
                reply = response_json["response"]
            else:
                 reply = str(response_json)

            self.messages.append({
                "role": "assistant",
                "content": reply
            })

            return reply
        except requests.exceptions.ConnectionError:
            logger.error("Local LLM Chat error: 无法连接到 Ollama 服务，请确认 Ollama 是否已启动并在 http://localhost:11434 监听。")
            return "抱歉，无法连接到本地大模型服务。"
        except requests.exceptions.Timeout:
            logger.error("Local LLM Chat error: 请求 Ollama 超时。")
            return "抱歉，本地大模型思考时间太长了。"
        except Exception as e:
            logger.error(f"Local LLM Chat error: {e}", exc_info=True)
            return "抱歉，我现在无法回答。"

    def reset_history(self):
        """
        重置对话历史，只保留 persona
        """
        self._load_persona()

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    llm = LLMClient()
    print(llm.chat("你好"))
