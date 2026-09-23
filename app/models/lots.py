"""Lote (tabla única para materia prima, semielaborado y producto) y lote
en uso."""

from datetime import date, datetime
from enum import Enum

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, SQLModel


class TipusLot(str, Enum):
    materia_primera = "materia_primera"
    semielaborat = "semielaborat"
    producte = "producte"


class TipusData(str, Enum):
    caducitat = "caducitat"
    consum_preferent = "consum_preferent"


class Lot(SQLModel, table=True):
    """Todos los lotes (materia prima, semielaborado, producto) viven en
    esta tabla; se distinguen por `tipus`. Los campos específicos de cada
    tipo son nullable — ver CLAUDE.md para qué grupo de campos corresponde
    a cada `tipus`. Nunca se hace UPDATE ni DELETE sobre un lote una vez
    creado (salvo anular_per_id, que marca una corrección): ver
    services/anulacio.py cuando exista."""

    __table_args__ = (
        CheckConstraint(
            "tipus != 'materia_primera' OR "
            "(ingredient_id IS NOT NULL AND proveidor_id IS NOT NULL AND lot_proveidor IS NOT NULL "
            "AND data_recepcio IS NOT NULL AND tipus_data IS NOT NULL)",
            name="ck_lot_materia_primera_camps",
        ),
        CheckConstraint(
            "tipus = 'materia_primera' OR "
            "(elaboracio_id IS NOT NULL AND quantitat IS NOT NULL AND unitat IS NOT NULL AND elaborat_at IS NOT NULL)",
            name="ck_lot_elaboracio_camps",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    tipus: TipusLot = Field(index=True)
    codi: str = Field(unique=True, index=True)
    creat_at: datetime
    responsable: str
    observacions: str | None = Field(default=None)
    anulat_per_id: int | None = Field(default=None, foreign_key="lot.id")

    # Materia prima (ficha 1)
    ingredient_id: int | None = Field(default=None, foreign_key="ingredient.id")
    proveidor_id: int | None = Field(default=None, foreign_key="proveidor.id")
    lot_proveidor: str | None = Field(default=None)
    data_recepcio: date | None = Field(default=None)
    caducitat: date | None = Field(default=None)
    tipus_data: TipusData | None = Field(default=None)

    # Semielaborado / producto (fichas 3 y 4)
    elaboracio_id: int | None = Field(default=None, foreign_key="elaboracio.id")
    quantitat: float | None = Field(default=None)
    unitat: str | None = Field(default=None)
    elaborat_at: datetime | None = Field(default=None)
    torn: str | None = Field(default=None)


class LotEnUs(SQLModel, table=True):
    """Ficha 2. Solo puede haber un registro con fi IS NULL por
    ingredient_id — índice único parcial declarado aquí (para que
    create_all en los tests lo cree igual que producción) y replicado a
    mano en alembic/versions/0001_initial_schema.py, porque no hay una
    sintaxis única portable entre SQLite y PostgreSQL para un índice
    parcial: cada motor usa su propio kwarg de dialecto."""

    __table_args__ = (
        Index(
            "uq_lotenus_ingredient_obert",
            "ingredient_id",
            unique=True,
            sqlite_where=text("fi IS NULL"),
            postgresql_where=text("fi IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.id", index=True)
    lot_id: int = Field(foreign_key="lot.id")
    inici: datetime
    fi: datetime | None = Field(default=None)
    observacions: str | None = Field(default=None)
