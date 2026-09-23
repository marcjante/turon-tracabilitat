"""Ficha 5 — cambio de lote a mitad de turno, devolución, alerta u otra
incidencia de trazabilidad."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas.incidencies import IncidenciaCreate, IncidenciaRead
from app.services.incidencies import crear_incidencia, llistar_incidencies

router = APIRouter()


@router.post("/incidencies", response_model=IncidenciaRead, status_code=201)
def crear(payload: IncidenciaCreate, session: Session = Depends(get_session)):
    return crear_incidencia(session, payload)


@router.get("/incidencies", response_model=list[IncidenciaRead])
def llistar(lot_afectat_id: int | None = None, session: Session = Depends(get_session)):
    return llistar_incidencies(session, lot_afectat_id)
