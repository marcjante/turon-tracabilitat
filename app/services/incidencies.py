"""Ficha 5 — incidencias. Al crear una, afectats_snapshot guarda la
trazabilidad hacia delante del lote afectado en ese momento (regla 7)."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.incidencies import Incidencia
from app.models.lots import Lot
from app.services.traca import traca_endavant


def crear_incidencia(session: Session, payload) -> Incidencia:
    # Idempotència (fase 5 offline): evita recalcular traca_endavant
    # (cost innecessari) i duplicar la incidència en un reintent.
    if payload.client_id is not None:
        existent = session.exec(select(Incidencia).where(Incidencia.client_id == payload.client_id)).first()
        if existent is not None:
            return existent

    if session.get(Lot, payload.lot_afectat_id) is None:
        raise HTTPException(status_code=404, detail="lot afectat no trobat")
    for camp, lot_id in (("lot_anterior_id", payload.lot_anterior_id), ("lot_nou_id", payload.lot_nou_id)):
        if lot_id is not None and session.get(Lot, lot_id) is None:
            raise HTTPException(status_code=404, detail=f"{camp} no correspon a cap lot")

    snapshot = traca_endavant(session, payload.lot_afectat_id)

    incidencia = Incidencia(
        tipus=payload.tipus,
        data_hora=payload.data_hora or datetime.now(timezone.utc),
        responsable=payload.responsable,
        lot_afectat_id=payload.lot_afectat_id,
        lot_anterior_id=payload.lot_anterior_id,
        lot_nou_id=payload.lot_nou_id,
        motiu=payload.motiu,
        mesura_adoptada=payload.mesura_adoptada,
        comprovacio=payload.comprovacio,
        comprovat_per=payload.comprovat_per,
        afectats_snapshot=snapshot,
        client_id=payload.client_id,
    )
    session.add(incidencia)
    session.commit()
    session.refresh(incidencia)
    return incidencia


def llistar_incidencies(session: Session, lot_afectat_id: int | None = None) -> list[Incidencia]:
    query = select(Incidencia)
    if lot_afectat_id is not None:
        query = query.where(Incidencia.lot_afectat_id == lot_afectat_id)
    return list(session.exec(query.order_by(Incidencia.data_hora.desc())).all())
