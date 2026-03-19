import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # Initialize the OpenAI client with Ark API settings
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=os.environ.get("ARK_API_KEY", "b6ef068e-6ae9-47f8-85d5-2ac15bf0860a")
        )
        self.model = "doubao-1-5-pro-32k-250115"
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
