"""Ficha 2 — lotes de materia prima en uso.

Regla de negocio 1: al abrir un lote en uso, en la misma transacción se
cierra (fi = inici del nuevo) el lote abierto del mismo ingrediente y se
abre el nuevo. Si el lote de materia prima está caducado, 422.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.lots import Lot, LotEnUs, TipusLot
from app.schemas.lots import LotEnUsCreate


def _lot_materia_primera_o_404(session: Session, lot_id: int, ingredient_id: int) -> Lot:
    lot = session.get(Lot, lot_id)
    if lot is None or lot.tipus != TipusLot.materia_primera or lot.anulat_per_id is not None:
        raise HTTPException(status_code=404, detail="lote de materia prima no encontrado")
    if lot.ingredient_id != ingredient_id:
        raise HTTPException(status_code=422, detail="el lote no pertenece a este ingrediente")
    return lot


def obrir_lot_en_us(session: Session, payload: LotEnUsCreate) -> LotEnUs:
    inici = payload.inici or datetime.now(timezone.utc)
    lot = _lot_materia_primera_o_404(session, payload.lot_id, payload.ingredient_id)

    if lot.caducitat is not None and lot.caducitat < inici.date():
        raise HTTPException(status_code=422, detail=f"el lote {lot.codi} está caducado ({lot.caducitat})")

    obert = session.exec(
        select(LotEnUs).where(LotEnUs.ingredient_id == payload.ingredient_id, LotEnUs.fi.is_(None))
    ).first()
    if obert is not None:
        obert.fi = inici
        session.add(obert)

    nou = LotEnUs(
        ingredient_id=payload.ingredient_id,
        lot_id=payload.lot_id,
        inici=inici,
        observacions=payload.observacions,
    )
    session.add(nou)
    session.commit()
    session.refresh(nou)
    return nou


def tancar_lot_en_us(session: Session, lot_en_us_id: int, fi: datetime) -> LotEnUs:
    """Cierra un lote en uso sin abrir uno nuevo (se acaba y todavía no
    hay sustituto)."""
    registre = session.get(LotEnUs, lot_en_us_id)
    if registre is None:
        raise HTTPException(status_code=404, detail="registro de lote en uso no encontrado")
    if registre.fi is not None:
        raise HTTPException(status_code=409, detail="este lote en uso ya estaba cerrado")
    registre.fi = fi
    session.add(registre)
    session.commit()
    session.refresh(registre)
    return registre


def lot_obert_per_ingredient(session: Session, ingredient_id: int, en: datetime) -> LotEnUs | None:
    """El lote en uso vigente para un ingrediente en un instante dado —
    usado por services/semielaborats.py y services/productes.py (Fase 2)
    para la vinculación automática."""
    return session.exec(
        select(LotEnUs).where(
            LotEnUs.ingredient_id == ingredient_id,
            LotEnUs.inici <= en,
            (LotEnUs.fi.is_(None)) | (LotEnUs.fi > en),
        )
    ).first()


def llistar_lots_en_us(session: Session) -> list[LotEnUs]:
    return list(session.exec(select(LotEnUs).where(LotEnUs.fi.is_(None)).order_by(LotEnUs.inici.desc())).all())


def llistar_historial(session: Session, ingredient_id: int | None = None) -> list[LotEnUs]:
    query = select(LotEnUs)
    if ingredient_id is not None:
        query = query.where(LotEnUs.ingredient_id == ingredient_id)
    return list(session.exec(query.order_by(LotEnUs.inici.desc())).all())
