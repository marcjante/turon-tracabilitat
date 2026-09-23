"""Ficha 1 — entrada de materias primas."""

from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models.lots import Lot, TipusLot
from app.schemas.lots import EntradaCreate


def crear_entrada(session: Session, payload: EntradaCreate) -> Lot:
    """El codi del lote es el lot_proveidor tal cual — lo asigna el
    proveedor, no lo generamos nosotros (a diferencia de semielaborados y
    productos, ficha 3/4).

    Idempotencia (fase 4 offline): si el payload trae client_id y ya
    existe un lote con ese client_id, se devuelve el existente en vez de
    crear un duplicado — necesario porque un dispositivo offline puede
    reintentar la misma creación si la respuesta se perdió en un corte
    de red a mitad de sincronizar."""
    if payload.client_id is not None:
        existent = session.exec(select(Lot).where(Lot.client_id == payload.client_id)).first()
        if existent is not None:
            return existent

    lot = Lot(
        tipus=TipusLot.materia_primera,
        codi=payload.lot_proveidor,
        creat_at=datetime.now(timezone.utc),
        responsable=payload.responsable,
        observacions=payload.observacions,
        ingredient_id=payload.ingredient_id,
        proveidor_id=payload.proveidor_id,
        lot_proveidor=payload.lot_proveidor,
        data_recepcio=payload.data_recepcio,
        caducitat=payload.caducitat,
        tipus_data=payload.tipus_data,
        client_id=payload.client_id,
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def llistar_entrades(
    session: Session,
    ingredient_id: int | None = None,
    desde: date | None = None,
    fins: date | None = None,
    caduca_en_dies: int | None = None,
) -> list[Lot]:
    query = select(Lot).where(Lot.tipus == TipusLot.materia_primera, Lot.anulat_per_id.is_(None))
    if ingredient_id is not None:
        query = query.where(Lot.ingredient_id == ingredient_id)
    if desde is not None:
        query = query.where(Lot.data_recepcio >= desde)
    if fins is not None:
        query = query.where(Lot.data_recepcio <= fins)
    if caduca_en_dies is not None:
        limit = datetime.now(timezone.utc).date() + timedelta(days=caduca_en_dies)
        query = query.where(Lot.caducitat <= limit)
    return list(session.exec(query.order_by(Lot.creat_at.desc())).all())
