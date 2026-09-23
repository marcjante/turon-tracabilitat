"""Ficha 1 — entrada de materias primas."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.db import get_session
from app.schemas.lots import EntradaCreate, EntradaRead
from app.services.entrades import crear_entrada, llistar_entrades

router = APIRouter()


@router.post("/entrades", response_model=EntradaRead, status_code=201)
def registrar_entrada(payload: EntradaCreate, session: Session = Depends(get_session)):
    try:
        return crear_entrada(session, payload)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail=f"ja existeix un lot amb codi '{payload.lot_proveidor}'")


@router.get("/entrades", response_model=list[EntradaRead])
def cercar_entrades(
    ingredient_id: int | None = None,
    desde: date | None = None,
    fins: date | None = None,
    caduca_en_dies: int | None = None,
    session: Session = Depends(get_session),
):
    return llistar_entrades(session, ingredient_id, desde, fins, caduca_en_dies)
