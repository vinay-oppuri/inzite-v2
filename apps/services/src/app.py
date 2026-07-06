from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/services")
def read_services():
    return {"services": ["research", "agent"]}
