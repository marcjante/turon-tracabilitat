"""Schemas para entradas de materia prima (ficha 1) y lotes en uso (ficha 2).

Los datetimes se guardan siempre en UTC (SQLModel lo exige: un datetime
naive en un INSERT falla). Si el cliente (la tablet) manda uno sin
información de zona horaria, se asume UTC en vez de rechazar la petición
— más tolerante para un formulario rápido de obrador."""

from datetime import date, datetime, timezone

from pydantic import BaseModel, field_validator, model_validator

from app.models.lots import TipusData


def _com_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class EntradaCreate(BaseModel):
    """El codi del lote de materia prima ES el lot_proveidor — no se
    genera, lo trae el propio albarán del proveedor."""

    ingredient_id: int
    proveidor_id: int
    lot_proveidor: str
    data_recepcio: date
    caducitat: date
    tipus_data: TipusData
    responsable: str
    observacions: str | None = None


class EntradaRead(BaseModel):
    id: int
    codi: str
    creat_at: datetime
    responsable: str
    observacions: str | None
    ingredient_id: int
    proveidor_id: int
    lot_proveidor: str
    data_recepcio: date
    caducitat: date
    tipus_data: TipusData
    anulat_per_id: int | None


class LotEnUsCreate(BaseModel):
    """Abre un lote de materia prima como "en uso" para su ingrediente —
    cierra automáticamente el que estuviera abierto (regla de negocio 1)."""

    ingredient_id: int
    lot_id: int
    inici: datetime | None = None
    observacions: str | None = None

    _inici_utc = field_validator("inici")(_com_utc)


class LotEnUsRead(BaseModel):
    id: int
    ingredient_id: int
    lot_id: int
    inici: datetime
    fi: datetime | None
    observacions: str | None


class LotEnUsTancar(BaseModel):
    """Cierre manual de un lote en uso, sin abrir uno nuevo (p. ej. se
    acaba el lote y no hay sustituto todavía)."""

    fi: datetime | None = None

    _fi_utc = field_validator("fi")(_com_utc)

    @model_validator(mode="after")
    def _default_fi(self):
        if self.fi is None:
            self.fi = datetime.now(timezone.utc)
        return self
