"""Schemas para gestión general de lotes: anular, búsqueda por codi,
corrección manual de consums."""

from datetime import date, datetime

from pydantic import BaseModel

from app.models.consums import OrigenConsum
from app.models.lots import TipusData, TipusLot


class LotAnularRequest(BaseModel):
    """El lote no se borra (regla 6): se marca anulat_per_id apuntando al
    lote nuevo (ya creado por separado, vía /entrades, /semielaborats o
    /productes) que lo corrige/sustituye."""

    lot_nou_id: int
    motiu: str | None = None


class LotRead(BaseModel):
    id: int
    tipus: TipusLot
    codi: str
    creat_at: datetime
    responsable: str
    observacions: str | None
    anulat_per_id: int | None
    ingredient_id: int | None
    proveidor_id: int | None
    lot_proveidor: str | None
    data_recepcio: date | None
    caducitat: date | None
    tipus_data: TipusData | None
    elaboracio_id: int | None
    quantitat: float | None
    unitat: str | None
    elaborat_at: datetime | None
    torn: str | None


class ConsumCreateRequest(BaseModel):
    lot_consumit_id: int
    responsable: str


class ConsumRead(BaseModel):
    lot_produit_id: int
    lot_consumit_id: int
    origen: OrigenConsum
    anulat_at: datetime | None
