"""Schemas para semielaborados (ficha 3) y productos (ficha 4)."""

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.utils import to_utc


class SemielaboratCreate(BaseModel):
    elaboracio_id: int
    quantitat: float
    unitat: str
    elaborat_at: datetime | None = None
    torn: str
    responsable: str
    observacions: str | None = None
    # UUID del dispositiu (fase 4/5 offline) — ver crear_produccio().
    client_id: str | None = None

    _elaborat_at_utc = field_validator("elaborat_at")(to_utc)


class ProducteCreate(SemielaboratCreate):
    """lots_semielaborats: {elaboracio_id del semielaborado (según receta):
    lot_id del lote concreto usado}. Obligatorio para cada componente
    semielaborado de la receta — no hay forma de inferirlo automáticamente
    (los semielaborados no tienen "lote en uso" como los ingredientes)."""

    lots_semielaborats: dict[int, int] = {}


class ElaboracioLotRead(BaseModel):
    id: int
    codi: str
    creat_at: datetime
    responsable: str
    observacions: str | None
    elaboracio_id: int
    quantitat: float
    unitat: str
    elaborat_at: datetime
    torn: str
    anulat_per_id: int | None
    client_id: str | None = None


class ElaboracioLotCreateResponse(ElaboracioLotRead):
    recepta_incompleta: bool
