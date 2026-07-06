
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self):
        self.client = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            max_output_tokens=1024,
        )

    def invoke_llm(self, prompt: str) -> str:
        response = self.client.invoke(prompt)
        return response.text