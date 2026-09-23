"""Gestión general de lotes: anular (regla 6), búsqueda por codi, y
corrección manual de consums (regla 3), con detección automática de
"canvi de lot a mig torn" (regla 4)."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.consums import Consum, OrigenConsum
from app.models.incidencies import Incidencia, TipusIncidencia
from app.models.lots import Lot
from app.services.traca import traca_endavant


def anular_lot(session: Session, lot_id: int, lot_nou_id: int, motiu: str | None) -> Lot:
    lot = session.get(Lot, lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="lot no trobat")
    if lot.anulat_per_id is not None:
        raise HTTPException(status_code=409, detail="aquest lot ja estava anul·lat")
    if lot_nou_id == lot_id:
        raise HTTPException(status_code=422, detail="un lot no es pot anul·lar a si mateix")
    nou = session.get(Lot, lot_nou_id)
    if nou is None:
        raise HTTPException(status_code=404, detail="lot nou no trobat")
    if nou.tipus != lot.tipus:
        raise HTTPException(status_code=422, detail="el lot nou ha de ser del mateix tipus que l'anul·lat")

    lot.anulat_per_id = nou.id
    if motiu:
        lot.observacions = (lot.observacions + " | " if lot.observacions else "") + f"Anul·lat: {motiu}"
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def cercar_lots_per_codi(session: Session, codi: str) -> list[Lot]:
    return list(
        session.exec(
            select(Lot)
            .where(Lot.codi.ilike(f"%{codi}%"), Lot.anulat_per_id.is_(None))
            .order_by(Lot.creat_at.desc())
        ).all()
    )


def afegir_consum_manual(session: Session, lot_produit_id: int, lot_consumit_id: int, responsable: str) -> Consum:
    if session.get(Lot, lot_produit_id) is None:
        raise HTTPException(status_code=404, detail="lot produït no trobat")
    consumit = session.get(Lot, lot_consumit_id)
    if consumit is None:
        raise HTTPException(status_code=404, detail="lot consumit no trobat")

    existent = session.get(Consum, (lot_produit_id, lot_consumit_id))
    if existent is not None and existent.anulat_at is None:
        raise HTTPException(status_code=409, detail="aquest consum ja existeix")

    # Regla 4: si ya había un consumo activo del mismo ingrediente para
    # este lote producido, es un cambio de lote a mitad de turno.
    canvi_lot_amb = None
    if consumit.ingredient_id is not None:
        actius = session.exec(
            select(Consum).where(Consum.lot_produit_id == lot_produit_id, Consum.anulat_at.is_(None))
        ).all()
        for actiu in actius:
            altre = session.get(Lot, actiu.lot_consumit_id)
            if altre is not None and altre.id != consumit.id and altre.ingredient_id == consumit.ingredient_id:
                canvi_lot_amb = altre
                break

    if existent is not None:
        existent.origen = OrigenConsum.manual
        existent.anulat_at = None
        session.add(existent)
    else:
        session.add(Consum(lot_produit_id=lot_produit_id, lot_consumit_id=lot_consumit_id, origen=OrigenConsum.manual))
    session.commit()

    if canvi_lot_amb is not None:
        session.add(Incidencia(
            tipus=TipusIncidencia.canvi_lot,
            data_hora=datetime.now(timezone.utc),
            responsable=responsable,
            lot_afectat_id=lot_produit_id,
            lot_anterior_id=canvi_lot_amb.id,
            lot_nou_id=consumit.id,
            motiu="Canvi de lot a mig torn (detectat en afegir un consum manual)",
            afectats_snapshot=traca_endavant(session, lot_produit_id),
        ))
        session.commit()

    return session.get(Consum, (lot_produit_id, lot_consumit_id))


def anular_consum(session: Session, lot_produit_id: int, lot_consumit_id: int) -> Consum:
    consum = session.get(Consum, (lot_produit_id, lot_consumit_id))
    if consum is None:
        raise HTTPException(status_code=404, detail="consum no trobat")
    if consum.anulat_at is not None:
        raise HTTPException(status_code=409, detail="aquest consum ja estava anul·lat")
    consum.anulat_at = datetime.now(timezone.utc)
    session.add(consum)
    session.commit()
    session.refresh(consum)
    return consum
