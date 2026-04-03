from fastapi import FastAPI

app = FastAPI(title="AI Learning Platform")


@app.get("/")
async def root():
    return {"message": "AI Learning Platform is running"}


