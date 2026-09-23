"""Punto de entrada de la API. uv run fastapi dev app/main.py"""

from fastapi import FastAPI

from app.routers import catalegs, entrades, incidencies, lots, lots_en_us, produccio, traca

app = FastAPI(title="Turon — API de trazabilidad")

app.include_router(catalegs.router, tags=["catalegs"])
app.include_router(entrades.router, tags=["entrades"])
app.include_router(lots_en_us.router, tags=["lots-en-us"])
app.include_router(produccio.router, tags=["produccio"])
app.include_router(lots.router, tags=["lots"])
app.include_router(traca.router, tags=["traca"])
app.include_router(incidencies.router, tags=["incidencies"])


@app.get("/health")
def health():
    return {"status": "ok"}
