"""Generación de códigos internos PREFIX-DDMMAA-NN (regla de negocio 5).

Seguro bajo concurrencia: en vez de calcular "el siguiente número" y
confiar en que nadie más lo tome antes, se intenta INSERTAR con ese
candidato y, si el commit falla por violar la unicidad de codi (otra
transacción concurrente ganó la carrera), se recalcula y se reintenta.
"""

from collections.abc import Callable
from datetime import date

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.lots import Lot

MAX_INTENTS = 5


def _prefix_dia(prefix: str, data: date) -> str:
    return f"{prefix}-{data.strftime('%d%m%y')}-"


def _seguent_candidat(session: Session, prefix: str, data: date, descartats: set[str]) -> str:
    patro = _prefix_dia(prefix, data)
    count = session.exec(select(func.count()).select_from(Lot).where(Lot.codi.like(f"{patro}%"))).one()
    numero = count + 1
    candidat = f"{patro}{numero:02d}"
    while candidat in descartats:
        numero += 1
        candidat = f"{patro}{numero:02d}"
    return candidat


def crear_lot_amb_codi(session: Session, prefix: str, data: date, construir_lot: Callable[[str], Lot]) -> Lot:
    """construir_lot(codi) debe devolver un Lot nuevo (sin persistir) con
    ese codi ya asignado. Reintenta hasta MAX_INTENTS veces si hay
    colisión de codi bajo concurrencia."""
    descartats: set[str] = set()
    for _ in range(MAX_INTENTS):
        codi = _seguent_candidat(session, prefix, data, descartats)
        lot = construir_lot(codi)
        session.add(lot)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            descartats.add(codi)
            continue
        session.refresh(lot)
        return lot
    raise RuntimeError(f"no s'ha pogut generar un codi únic per a '{prefix}' després de {MAX_INTENTS} intents")
