"""Schemas para trazabilidad hacia delante/atrás (ficha 5)."""

from datetime import date, datetime

from pydantic import BaseModel


class TracaItem(BaseModel):
    lot_id: int
    codi: str
    nom: str | None
    data: date | datetime | None
    quantitat: float | None


class TracaResponse(BaseModel):
    lot_origen_id: int
    materia_primera: list[TracaItem]
    semielaborat: list[TracaItem]
    producte: list[TracaItem]
