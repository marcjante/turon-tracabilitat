"""Modelos SQLModel. Importar todos aquí para que Alembic los detecte al
generar migraciones (target_metadata en alembic/env.py depende de esto)."""

from app.models.catalegs import Elaboracio, Ingredient, Proveidor, Recepta, TipusElaboracio
from app.models.consums import Consum, OrigenConsum
from app.models.incidencies import Incidencia, TipusIncidencia
from app.models.lots import Lot, LotEnUs, TipusData, TipusLot

__all__ = [
    "Ingredient",
    "Proveidor",
    "Elaboracio",
    "TipusElaboracio",
    "Recepta",
    "Lot",
    "TipusLot",
    "TipusData",
    "LotEnUs",
    "Consum",
    "OrigenConsum",
    "Incidencia",
    "TipusIncidencia",
]
