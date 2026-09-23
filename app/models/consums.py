"""Grafo de consumos: qué lote se consumió para producir qué otro lote.
Es la tabla sobre la que corre la trazabilidad (WITH RECURSIVE, Fase 3).
Nunca se hace UPDATE ni DELETE — una corrección crea filas nuevas con
origen='manual' y dependerá de la Fase 2/3 decidir cómo se marcan como
sustituidas (no se implementa en la Fase 1)."""

from enum import Enum

from sqlmodel import Field, SQLModel


class OrigenConsum(str, Enum):
    automatic = "automatic"
    manual = "manual"


class Consum(SQLModel, table=True):
    lot_produit_id: int = Field(foreign_key="lot.id", primary_key=True)
    lot_consumit_id: int = Field(foreign_key="lot.id", primary_key=True)
    origen: OrigenConsum
