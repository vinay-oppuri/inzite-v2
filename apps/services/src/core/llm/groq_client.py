from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

class GroqClient:
    def __init__(self):
        self.client = ChatGroq(
            model="qwen/qwen3-32b",
        )

    def invoke_llm(self, prompt: str) -> str:
        response = self.client.invoke(prompt)
        return response.text