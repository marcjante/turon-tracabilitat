"""Ficha 2 — lotes de materia prima en uso."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas.lots import LotEnUsCreate, LotEnUsRead, LotEnUsTancar
from app.services.lots_en_us import (
    llistar_historial,
    llistar_lots_en_us,
    obrir_lot_en_us,
    tancar_lot_en_us,
)

router = APIRouter()


@router.post("/lots-en-us", response_model=LotEnUsRead, status_code=201)
def obrir(payload: LotEnUsCreate, session: Session = Depends(get_session)):
    return obrir_lot_en_us(session, payload)


@router.get("/lots-en-us", response_model=list[LotEnUsRead])
def llistar(session: Session = Depends(get_session)):
    """Solo los lotes en uso actualmente abiertos (fi IS NULL) — para el
    historial completo, ver /lots-en-us/historial."""
    return llistar_lots_en_us(session)


@router.get("/lots-en-us/historial", response_model=list[LotEnUsRead])
def historial(ingredient_id: int | None = None, session: Session = Depends(get_session)):
    return llistar_historial(session, ingredient_id)


@router.post("/lots-en-us/{lot_en_us_id}/tancar", response_model=LotEnUsRead)
def tancar(lot_en_us_id: int, payload: LotEnUsTancar, session: Session = Depends(get_session)):
    return tancar_lot_en_us(session, lot_en_us_id, payload.fi)
