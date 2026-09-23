"""Ficha 5: cambio de lote a mitad de turno, devolución, alerta u otra
incidencia de trazabilidad."""

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class TipusIncidencia(str, Enum):
    canvi_lot = "canvi_lot"
    devolucio = "devolucio"
    alerta = "alerta"
    altra = "altra"


class Incidencia(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tipus: TipusIncidencia
    data_hora: datetime
    responsable: str
    lot_afectat_id: int = Field(foreign_key="lot.id")
    lot_anterior_id: int | None = Field(default=None, foreign_key="lot.id")
    lot_nou_id: int | None = Field(default=None, foreign_key="lot.id")
    motiu: str
    mesura_adoptada: str | None = Field(default=None)
    comprovacio: bool = Field(default=False)
    comprovat_per: str | None = Field(default=None)
    # Trazabilidad hacia delante del lote afectado en el momento de crear
    # la incidencia — ver services/traca.py cuando exista (Fase 3).
    afectats_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    client_id: str | None = Field(default=None, unique=True, index=True)
