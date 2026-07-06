from fastapi import FastAPI
from src.core.pipeline import Pipeline

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the LLM Pipeline API!"}

@app.get("/run_pipeline")
def run_pipeline(prompt: str):
    pipeline = Pipeline()
    response = pipeline.run(prompt)
    return {"response": response}