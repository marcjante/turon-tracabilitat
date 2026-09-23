"""Punto de entrada de la API. uv run fastapi dev app/main.py"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.routers import catalegs, entrades, incidencies, lots, lots_en_us, produccio, traca

app = FastAPI(title="Turon — API de trazabilidad")

# Sin restricción de origen: esta API no tiene autenticación todavía
# ("Sin autenticación en esta versión", CLAUDE.md), así que limitar CORS
# no la protegería de verdad (cualquiera puede llamarla directamente, sin
# pasar por un navegador) — solo bloquearía al propio frontend legítimo.
# Cuando haya autenticación, restringir esto a los orígenes reales.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalegs.router, tags=["catalegs"])
app.include_router(entrades.router, tags=["entrades"])
app.include_router(lots_en_us.router, tags=["lots-en-us"])
app.include_router(produccio.router, tags=["produccio"])
app.include_router(lots.router, tags=["lots"])
app.include_router(traca.router, tags=["traca"])
app.include_router(incidencies.router, tags=["incidencies"])


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health")
def health():
    return {"status": "ok"}
