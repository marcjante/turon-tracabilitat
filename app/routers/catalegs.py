"""CRUD de catálogos: ingredientes, proveedores, elaboraciones, recetas."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.models.catalegs import Elaboracio, Ingredient, Proveidor, Recepta
from app.schemas.catalegs import (
    ElaboracioCreate,
    ElaboracioRead,
    ElaboracioUpdate,
    IngredientCreate,
    IngredientRead,
    IngredientUpdate,
    ProveidorCreate,
    ProveidorRead,
    ProveidorUpdate,
    ReceptaCreate,
    ReceptaRead,
)

router = APIRouter()


# --- Ingredients ---

@router.post("/ingredients", response_model=IngredientRead, status_code=201)
def crear_ingredient(payload: IngredientCreate, session: Session = Depends(get_session)):
    ingredient = Ingredient.model_validate(payload)
    session.add(ingredient)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="ja existeix un ingredient amb aquest nom")
    session.refresh(ingredient)
    return ingredient


@router.get("/ingredients", response_model=list[IngredientRead])
def llistar_ingredients(actiu: bool | None = None, session: Session = Depends(get_session)):
    query = select(Ingredient)
    if actiu is not None:
        query = query.where(Ingredient.actiu == actiu)
    return session.exec(query.order_by(Ingredient.nom)).all()


@router.get("/ingredients/{ingredient_id}", response_model=IngredientRead)
def obtenir_ingredient(ingredient_id: int, session: Session = Depends(get_session)):
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="ingredient no trobat")
    return ingredient


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientRead)
def actualitzar_ingredient(ingredient_id: int, payload: IngredientUpdate, session: Session = Depends(get_session)):
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="ingredient no trobat")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(ingredient, key, value)
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


@router.delete("/ingredients/{ingredient_id}", status_code=204)
def eliminar_ingredient(ingredient_id: int, session: Session = Depends(get_session)):
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="ingredient no trobat")
    session.delete(ingredient)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="no es pot eliminar: té lots o receptes associades")


# --- Proveïdors ---

@router.post("/proveidors", response_model=ProveidorRead, status_code=201)
def crear_proveidor(payload: ProveidorCreate, session: Session = Depends(get_session)):
    proveidor = Proveidor.model_validate(payload)
    session.add(proveidor)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="ja existeix un proveïdor amb aquest nom")
    session.refresh(proveidor)
    return proveidor


@router.get("/proveidors", response_model=list[ProveidorRead])
def llistar_proveidors(actiu: bool | None = None, session: Session = Depends(get_session)):
    query = select(Proveidor)
    if actiu is not None:
        query = query.where(Proveidor.actiu == actiu)
    return session.exec(query.order_by(Proveidor.nom)).all()


@router.get("/proveidors/{proveidor_id}", response_model=ProveidorRead)
def obtenir_proveidor(proveidor_id: int, session: Session = Depends(get_session)):
    proveidor = session.get(Proveidor, proveidor_id)
    if proveidor is None:
        raise HTTPException(status_code=404, detail="proveïdor no trobat")
    return proveidor


@router.patch("/proveidors/{proveidor_id}", response_model=ProveidorRead)
def actualitzar_proveidor(proveidor_id: int, payload: ProveidorUpdate, session: Session = Depends(get_session)):
    proveidor = session.get(Proveidor, proveidor_id)
    if proveidor is None:
        raise HTTPException(status_code=404, detail="proveïdor no trobat")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(proveidor, key, value)
    session.add(proveidor)
    session.commit()
    session.refresh(proveidor)
    return proveidor


@router.delete("/proveidors/{proveidor_id}", status_code=204)
def eliminar_proveidor(proveidor_id: int, session: Session = Depends(get_session)):
    proveidor = session.get(Proveidor, proveidor_id)
    if proveidor is None:
        raise HTTPException(status_code=404, detail="proveïdor no trobat")
    session.delete(proveidor)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="no es pot eliminar: té lots associats")


# --- Elaboracions ---

@router.post("/elaboracions", response_model=ElaboracioRead, status_code=201)
def crear_elaboracio(payload: ElaboracioCreate, session: Session = Depends(get_session)):
    elaboracio = Elaboracio.model_validate(payload)
    session.add(elaboracio)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="ja existeix una elaboració amb aquest nom o prefix")
    session.refresh(elaboracio)
    return elaboracio


@router.get("/elaboracions", response_model=list[ElaboracioRead])
def llistar_elaboracions(
    tipus: str | None = None, actiu: bool | None = None, session: Session = Depends(get_session)
):
    query = select(Elaboracio)
    if tipus is not None:
        query = query.where(Elaboracio.tipus == tipus)
    if actiu is not None:
        query = query.where(Elaboracio.actiu == actiu)
    return session.exec(query.order_by(Elaboracio.nom)).all()


@router.get("/elaboracions/{elaboracio_id}", response_model=ElaboracioRead)
def obtenir_elaboracio(elaboracio_id: int, session: Session = Depends(get_session)):
    elaboracio = session.get(Elaboracio, elaboracio_id)
    if elaboracio is None:
        raise HTTPException(status_code=404, detail="elaboració no trobada")
    return elaboracio


@router.patch("/elaboracions/{elaboracio_id}", response_model=ElaboracioRead)
def actualitzar_elaboracio(elaboracio_id: int, payload: ElaboracioUpdate, session: Session = Depends(get_session)):
    elaboracio = session.get(Elaboracio, elaboracio_id)
    if elaboracio is None:
        raise HTTPException(status_code=404, detail="elaboració no trobada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(elaboracio, key, value)
    session.add(elaboracio)
    session.commit()
    session.refresh(elaboracio)
    return elaboracio


@router.delete("/elaboracions/{elaboracio_id}", status_code=204)
def eliminar_elaboracio(elaboracio_id: int, session: Session = Depends(get_session)):
    elaboracio = session.get(Elaboracio, elaboracio_id)
    if elaboracio is None:
        raise HTTPException(status_code=404, detail="elaboració no trobada")
    session.delete(elaboracio)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="no es pot eliminar: té lots o receptes associades")


# --- Receptes ---

@router.post("/receptes", response_model=ReceptaRead, status_code=201)
def crear_recepta(payload: ReceptaCreate, session: Session = Depends(get_session)):
    if (payload.ingredient_id is None) == (payload.semielaborat_id is None):
        raise HTTPException(status_code=422, detail="cal indicar exactament un de ingredient_id o semielaborat_id")
    recepta = Recepta.model_validate(payload)
    session.add(recepta)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="aquest component ja forma part de la recepta")
    session.refresh(recepta)
    return recepta


@router.get("/receptes", response_model=list[ReceptaRead])
def llistar_receptes(elaboracio_id: int | None = None, session: Session = Depends(get_session)):
    query = select(Recepta)
    if elaboracio_id is not None:
        query = query.where(Recepta.elaboracio_id == elaboracio_id)
    return session.exec(query).all()


@router.delete("/receptes/{recepta_id}", status_code=204)
def eliminar_recepta(recepta_id: int, session: Session = Depends(get_session)):
    recepta = session.get(Recepta, recepta_id)
    if recepta is None:
        raise HTTPException(status_code=404, detail="recepta no trobada")
    session.delete(recepta)
    session.commit()
