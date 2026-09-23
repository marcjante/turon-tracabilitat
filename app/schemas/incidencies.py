"""Ficha 5 — cambio de lote a mitad de turno, devolución, alerta u otra
incidencia de trazabilidad."""

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.incidencies import TipusIncidencia
from app.utils import to_utc


class IncidenciaCreate(BaseModel):
    tipus: TipusIncidencia
    data_hora: datetime | None = None
    responsable: str
    lot_afectat_id: int
    lot_anterior_id: int | None = None
    lot_nou_id: int | None = None
    motiu: str
    mesura_adoptada: str | None = None
    comprovacio: bool = False
    comprovat_per: str | None = None
    client_id: str | None = None

    _data_hora_utc = field_validator("data_hora")(to_utc)


class IncidenciaRead(BaseModel):
    id: int
    tipus: TipusIncidencia
    data_hora: datetime
    responsable: str
    lot_afectat_id: int
    lot_anterior_id: int | None
    lot_nou_id: int | None
    motiu: str
    mesura_adoptada: str | None
    comprovacio: bool
    comprovat_per: str | None
    afectats_snapshot: dict
    client_id: str | None = None
