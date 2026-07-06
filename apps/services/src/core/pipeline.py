from src.core.llm.gemini_client import GeminiClient
from src.core.llm.groq_client import GroqClient

class Pipeline:
    def __init__(self):
        # self.llm = GeminiClient()
        self.llm = GroqClient()

    def run(self, prompt: str) -> str:
        response = self.llm.invoke_llm(prompt)
        return response
