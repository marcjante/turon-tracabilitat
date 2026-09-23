"""Ficha 5 — trazabilidad hacia delante y hacia atrás."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas.traca import TracaResponse
from app.services.traca import traca_endavant, traca_enrere

router = APIRouter()


@router.get("/traca/endavant/{lot_id}", response_model=TracaResponse)
def endavant(lot_id: int, session: Session = Depends(get_session)):
    resultat = traca_endavant(session, lot_id)
    return TracaResponse(lot_origen_id=lot_id, **resultat)


@router.get("/traca/enrere/{lot_id}", response_model=TracaResponse)
def enrere(lot_id: int, session: Session = Depends(get_session)):
    resultat = traca_enrere(session, lot_id)
    return TracaResponse(lot_origen_id=lot_id, **resultat)
