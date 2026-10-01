from fastapi import FastAPI

app = FastAPI(title="逃离校园实验室", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "campus-lab-escape"}
