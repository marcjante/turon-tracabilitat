"""Ficha 5 — trazabilidad hacia delante y hacia atrás, con WITH RECURSIVE
sobre consum (misma sintaxis en SQLite y PostgreSQL vía sqlalchemy .cte(),
sin nada específico de un motor)."""

from fastapi import HTTPException
from sqlalchemy import select as sa_select
from sqlmodel import Session, select

from app.models.catalegs import Elaboracio, Ingredient
from app.models.consums import Consum
from app.models.lots import Lot, TipusLot


def _lot_o_404(session: Session, lot_id: int) -> Lot:
    lot = session.get(Lot, lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="lot no trobat")
    return lot


def _agrupar(session: Session, lot_ids: set[int]) -> dict:
    agrupat = {"materia_primera": [], "semielaborat": [], "producte": []}
    if not lot_ids:
        return agrupat

    ingredients = {i.id: i.nom for i in session.exec(select(Ingredient)).all()}
    elaboracions = {e.id: e.nom for e in session.exec(select(Elaboracio)).all()}

    lots = session.exec(select(Lot).where(Lot.id.in_(lot_ids))).all()
    for lot in sorted(lots, key=lambda item: (item.tipus.value, item.codi)):
        if lot.tipus == TipusLot.materia_primera:
            nom = ingredients.get(lot.ingredient_id)
            data = lot.data_recepcio
            quantitat = None
        else:
            nom = elaboracions.get(lot.elaboracio_id)
            data = lot.elaborat_at
            quantitat = lot.quantitat
        agrupat[lot.tipus.value].append({
            "lot_id": lot.id, "codi": lot.codi, "nom": nom,
            # ISO string, no el objeto date/datetime crudo: este dict se
            # usa tal cual como afectats_snapshot (columna JSON) y json
            # no sabe serializar date/datetime. TracaItem lo vuelve a
            # parsear sin problema al construir la respuesta de la API.
            "data": data.isoformat() if data is not None else None,
            "quantitat": quantitat,
        })
    return agrupat


def traca_endavant(session: Session, lot_id: int) -> dict:
    """Todos los lotes que han consumido lot_id, directa o indirectamente
    (farina -> planxes -> braços, si se pregunta por el lote de farina)."""
    _lot_o_404(session, lot_id)

    base = sa_select(Consum.lot_produit_id, Consum.lot_consumit_id).where(
        Consum.lot_consumit_id == lot_id, Consum.anulat_at.is_(None)
    )
    cte = base.cte("forward", recursive=True)
    recursiu = sa_select(Consum.lot_produit_id, Consum.lot_consumit_id).where(
        Consum.lot_consumit_id == cte.c.lot_produit_id, Consum.anulat_at.is_(None)
    )
    cte = cte.union_all(recursiu)

    lot_ids = {row[0] for row in session.execute(sa_select(cte.c.lot_produit_id)).all()}
    return _agrupar(session, lot_ids)


def traca_enrere(session: Session, lot_id: int) -> dict:
    """Todos los lotes consumidos (directa o indirectamente) hasta llegar
    a la materia prima, para producir lot_id."""
    _lot_o_404(session, lot_id)

    base = sa_select(Consum.lot_produit_id, Consum.lot_consumit_id).where(
        Consum.lot_produit_id == lot_id, Consum.anulat_at.is_(None)
    )
    cte = base.cte("backward", recursive=True)
    recursiu = sa_select(Consum.lot_produit_id, Consum.lot_consumit_id).where(
        Consum.lot_produit_id == cte.c.lot_consumit_id, Consum.anulat_at.is_(None)
    )
    cte = cte.union_all(recursiu)

    lot_ids = {row[0] for row in session.execute(sa_select(cte.c.lot_consumit_id)).all()}
    return _agrupar(session, lot_ids)
