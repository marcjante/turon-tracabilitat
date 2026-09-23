"""Ficha 3 — producción de semielaborados; ficha 4 — producción diaria."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models.catalegs import TipusElaboracio
from app.models.lots import Lot, TipusLot
from app.schemas.produccio import (
    ElaboracioLotCreateResponse,
    ElaboracioLotRead,
    ProducteCreate,
    SemielaboratCreate,
)
from app.services.produccio import crear_produccio

router = APIRouter()


def _lot_dict(lot: Lot) -> dict:
    """No usamos lot.model_dump() aquí: tras session.refresh(), SQLModel
    puede devolver un dump vacío/incompleto en una instancia de tabla ya
    persistida (los atributos quedan "expirados" tras el commit y
    model_dump no dispara la recarga perezosa de SQLAlchemy). El acceso
    explícito sí la dispara."""
    return {
        "id": lot.id, "codi": lot.codi, "creat_at": lot.creat_at, "responsable": lot.responsable,
        "observacions": lot.observacions, "elaboracio_id": lot.elaboracio_id, "quantitat": lot.quantitat,
        "unitat": lot.unitat, "elaborat_at": lot.elaborat_at, "torn": lot.torn, "anulat_per_id": lot.anulat_per_id,
    }


@router.post("/semielaborats", response_model=ElaboracioLotCreateResponse, status_code=201)
def crear_semielaborat(payload: SemielaboratCreate, session: Session = Depends(get_session)):
    lot, recepta_incompleta = crear_produccio(session, payload, TipusElaboracio.semielaborat)
    return ElaboracioLotCreateResponse(**_lot_dict(lot), recepta_incompleta=recepta_incompleta)


@router.get("/semielaborats", response_model=list[ElaboracioLotRead])
def llistar_semielaborats(session: Session = Depends(get_session)):
    query = select(Lot).where(Lot.tipus == TipusLot.semielaborat, Lot.anulat_per_id.is_(None))
    return session.exec(query.order_by(Lot.creat_at.desc())).all()


@router.post("/productes", response_model=ElaboracioLotCreateResponse, status_code=201)
def crear_producte(payload: ProducteCreate, session: Session = Depends(get_session)):
    lot, recepta_incompleta = crear_produccio(session, payload, TipusElaboracio.producte, payload.lots_semielaborats)
    return ElaboracioLotCreateResponse(**_lot_dict(lot), recepta_incompleta=recepta_incompleta)


@router.get("/productes", response_model=list[ElaboracioLotRead])
def llistar_productes(session: Session = Depends(get_session)):
    query = select(Lot).where(Lot.tipus == TipusLot.producte, Lot.anulat_per_id.is_(None))
    return session.exec(query.order_by(Lot.creat_at.desc())).all()
