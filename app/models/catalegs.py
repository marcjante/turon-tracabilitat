"""Catálogos: ingredientes, proveedores, elaboraciones (semielaborados y
productos) y sus recetas."""

from enum import Enum

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel


class TipusElaboracio(str, Enum):
    semielaborat = "semielaborat"
    producte = "producte"


class Ingredient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nom: str = Field(unique=True, index=True)
    actiu: bool = Field(default=True)


class Proveidor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nom: str = Field(unique=True, index=True)
    actiu: bool = Field(default=True)


class Elaboracio(SQLModel, table=True):
    """Una elaboración es un semielaborado (Crema, Planxes...) o un
    producto final (Melindros, Braços...). prefix_lot es el prefijo usado
    para generar el codi de cada lote (p. ej. CRE-140826-01)."""

    id: int | None = Field(default=None, primary_key=True)
    nom: str = Field(unique=True, index=True)
    tipus: TipusElaboracio
    prefix_lot: str = Field(unique=True, index=True)
    actiu: bool = Field(default=True)


class Recepta(SQLModel, table=True):
    """Un ingrediente de la receta de una elaboración: o bien una materia
    prima (ingredient_id) o bien un semielaborado (semielaborat_id) —
    exactamente uno de los dos, nunca ambos ni ninguno."""

    __table_args__ = (
        CheckConstraint(
            "(ingredient_id IS NOT NULL) != (semielaborat_id IS NOT NULL)",
            name="ck_recepta_un_sol_component",
        ),
        UniqueConstraint("elaboracio_id", "ingredient_id", name="uq_recepta_elaboracio_ingredient"),
        UniqueConstraint("elaboracio_id", "semielaborat_id", name="uq_recepta_elaboracio_semielaborat"),
    )

    id: int | None = Field(default=None, primary_key=True)
    elaboracio_id: int = Field(foreign_key="elaboracio.id", index=True)
    ingredient_id: int | None = Field(default=None, foreign_key="ingredient.id")
    # Referencia a OTRA Elaboracio de tipus=semielaborat que se usa como
    # componente (p. ej. la receta de Braços usa Planxes y Trufa).
    semielaborat_id: int | None = Field(default=None, foreign_key="elaboracio.id")
