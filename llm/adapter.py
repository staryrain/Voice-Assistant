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
        base_url = llm_config.get("base_url", "")
        api_key = llm_config.get("api_key", "")
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=os.environ.get("ARK_API_KEY", api_key)
        )
        self.model = llm_config.get("model", "")
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
