"""Schemas de entrada/salida para los catálogos. Separados de los modelos
de tabla (app.models) para no exponer columnas internas y poder validar
solo lo que el cliente debe mandar."""

from pydantic import BaseModel

from app.models.catalegs import TipusElaboracio


class IngredientCreate(BaseModel):
    nom: str
    actiu: bool = True


class IngredientUpdate(BaseModel):
    nom: str | None = None
    actiu: bool | None = None


class IngredientRead(BaseModel):
    id: int
    nom: str
    actiu: bool


class ProveidorCreate(BaseModel):
    nom: str
    actiu: bool = True


class ProveidorUpdate(BaseModel):
    nom: str | None = None
    actiu: bool | None = None


class ProveidorRead(BaseModel):
    id: int
    nom: str
    actiu: bool


class ElaboracioCreate(BaseModel):
    nom: str
    tipus: TipusElaboracio
    prefix_lot: str
    actiu: bool = True


class ElaboracioUpdate(BaseModel):
    nom: str | None = None
    prefix_lot: str | None = None
    actiu: bool | None = None


class ElaboracioRead(BaseModel):
    id: int
    nom: str
    tipus: TipusElaboracio
    prefix_lot: str
    actiu: bool


class ReceptaCreate(BaseModel):
    elaboracio_id: int
    ingredient_id: int | None = None
    semielaborat_id: int | None = None


class ReceptaRead(BaseModel):
    id: int
    elaboracio_id: int
    ingredient_id: int | None
    semielaborat_id: int | None
