"""Punto de entrada de la API. uv run fastapi dev app/main.py"""

from fastapi import FastAPI

from app.routers import catalegs, entrades, lots_en_us

app = FastAPI(title="Turon — API de trazabilidad")

app.include_router(catalegs.router, tags=["catalegs"])
app.include_router(entrades.router, tags=["entrades"])
app.include_router(lots_en_us.router, tags=["lots-en-us"])


@app.get("/health")
def health():
    return {"status": "ok"}
