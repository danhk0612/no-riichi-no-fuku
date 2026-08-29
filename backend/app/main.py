from fastapi import FastAPI

app = FastAPI(title="No Riichi No Fuku API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
