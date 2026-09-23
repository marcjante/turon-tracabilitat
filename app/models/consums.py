"""Grafo de consumos: qué lote se consumió para producir qué otro lote.
Es la tabla sobre la que corre la trazabilidad (WITH RECURSIVE, Fase 3).

Nunca se hace UPDATE ni DELETE sobre una fila de consum — "DELETE
/lots/{id}/consums (el DELETE anula, no borra)" del enunciado se
implementa marcando anulat_at en vez de borrar la fila; las consultas de
trazabilidad y las correcciones excluyen los consums anulados por
defecto, pero la fila sigue ahí para el historial."""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class OrigenConsum(str, Enum):
    automatic = "automatic"
    manual = "manual"


class Consum(SQLModel, table=True):
    lot_produit_id: int = Field(foreign_key="lot.id", primary_key=True)
    lot_consumit_id: int = Field(foreign_key="lot.id", primary_key=True)
    origen: OrigenConsum
    anulat_at: datetime | None = Field(default=None)
