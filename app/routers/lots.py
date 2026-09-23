"""Gestión general de lotes: anular, búsqueda por codi, corrección de consums."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas.lots_gestio import ConsumCreateRequest, ConsumRead, LotAnularRequest, LotRead
from app.services.lots import afegir_consum_manual, anular_consum, anular_lot, cercar_lots_per_codi

router = APIRouter()


@router.get("/lots/cerca", response_model=list[LotRead])
def cerca(codi: str, session: Session = Depends(get_session)):
    return cercar_lots_per_codi(session, codi)


@router.post("/lots/{lot_id}/anular", response_model=LotRead)
def anular(lot_id: int, payload: LotAnularRequest, session: Session = Depends(get_session)):
    return anular_lot(session, lot_id, payload.lot_nou_id, payload.motiu)


@router.post("/lots/{lot_id}/consums", response_model=ConsumRead, status_code=201)
def afegir_consum(lot_id: int, payload: ConsumCreateRequest, session: Session = Depends(get_session)):
    return afegir_consum_manual(session, lot_id, payload.lot_consumit_id, payload.responsable)


@router.delete("/lots/{lot_id}/consums", response_model=ConsumRead)
def eliminar_consum(lot_id: int, lot_consumit_id: int, session: Session = Depends(get_session)):
    return anular_consum(session, lot_id, lot_consumit_id)
