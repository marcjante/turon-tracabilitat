"""Ficha 3 (semielaborados) y ficha 4 (productos): vinculación automática
con los lotes en uso y generación de código interno (regla de negocio 2 y 5).

Vinculación de componentes semielaborados en la receta de un producto
(p. ej. Braços usa Planxes + Trufa): a diferencia de los ingredientes, un
semielaborado no tiene un "lote en uso" (ficha 2 solo existe para
materias primas), así que no hay forma de inferirlo automáticamente. El
cliente debe indicar qué lote de cada componente semielaborado se usó
(`lots_semielaborats`); si falta alguno requerido por la receta, 409 — el
mismo tratamiento que un ingrediente sin lote abierto, para no dejar
huecos en la trazabilidad hacia atrás (Fase 3).
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.catalegs import Elaboracio, Ingredient, Recepta, TipusElaboracio
from app.models.consums import Consum, OrigenConsum
from app.models.lots import Lot, LotEnUs, TipusLot
from app.services.codis import crear_lot_amb_codi
from app.services.lots_en_us import lot_obert_per_ingredient


def _tots_els_lots_oberts(session: Session, en: datetime) -> list[LotEnUs]:
    return list(
        session.exec(
            select(LotEnUs).where(LotEnUs.inici <= en, (LotEnUs.fi.is_(None)) | (LotEnUs.fi > en))
        ).all()
    )


def _resoldre_consums(
    session: Session, elaboracio: Elaboracio, elaborat_at: datetime, lots_semielaborats: dict[int, int]
) -> tuple[list[int], bool]:
    """Devuelve (lista de lot_id consumidos, recepta_incompleta)."""
    recepta = list(session.exec(select(Recepta).where(Recepta.elaboracio_id == elaboracio.id)).all())

    if not recepta:
        oberts = _tots_els_lots_oberts(session, elaborat_at)
        return [obert.lot_id for obert in oberts], True

    consumits: list[int] = []
    for component in recepta:
        if component.ingredient_id is not None:
            obert = lot_obert_per_ingredient(session, component.ingredient_id, elaborat_at)
            if obert is None:
                ingredient = session.get(Ingredient, component.ingredient_id)
                nom = ingredient.nom if ingredient else component.ingredient_id
                raise HTTPException(status_code=409, detail=f"no hi ha cap lot obert per a l'ingredient '{nom}'")
            consumits.append(obert.lot_id)
        else:
            lot_id = lots_semielaborats.get(component.semielaborat_id)
            if lot_id is None:
                semi = session.get(Elaboracio, component.semielaborat_id)
                nom = semi.nom if semi else component.semielaborat_id
                raise HTTPException(status_code=409, detail=f"cal indicar el lot utilitzat del semielaborat '{nom}'")
            lot_semi = session.get(Lot, lot_id)
            if (
                lot_semi is None
                or lot_semi.tipus != TipusLot.semielaborat
                or lot_semi.elaboracio_id != component.semielaborat_id
                or lot_semi.anulat_per_id is not None
            ):
                raise HTTPException(status_code=422, detail=f"el lot indicat per al semielaborat {component.semielaborat_id} no és vàlid")
            consumits.append(lot_id)
    return consumits, False


def crear_produccio(
    session: Session,
    payload,
    tipus_esperat: TipusElaboracio,
    lots_semielaborats: dict[int, int] | None = None,
) -> tuple[Lot, bool]:
    # Idempotència (fase 5 offline): evita repetir _resoldre_consums
    # (podria "consumir" un lot en ús diferent si l'estat ha canviat
    # entre l'intent original i el reintent) i generar un codi nou de
    # franc en un reintent.
    if getattr(payload, "client_id", None) is not None:
        existent = session.exec(select(Lot).where(Lot.client_id == payload.client_id)).first()
        if existent is not None:
            return existent, False

    elaboracio = session.get(Elaboracio, payload.elaboracio_id)
    if elaboracio is None or not elaboracio.actiu:
        raise HTTPException(status_code=404, detail="elaboració no trobada")
    if elaboracio.tipus != tipus_esperat:
        raise HTTPException(status_code=422, detail=f"'{elaboracio.nom}' no és de tipus {tipus_esperat.value}")

    elaborat_at = payload.elaborat_at or datetime.now(timezone.utc)
    consumits, recepta_incompleta = _resoldre_consums(session, elaboracio, elaborat_at, lots_semielaborats or {})

    def _construir(codi: str) -> Lot:
        return Lot(
            tipus=TipusLot(tipus_esperat.value),
            codi=codi,
            creat_at=datetime.now(timezone.utc),
            responsable=payload.responsable,
            observacions=payload.observacions,
            elaboracio_id=elaboracio.id,
            quantitat=payload.quantitat,
            unitat=payload.unitat,
            elaborat_at=elaborat_at,
            torn=payload.torn,
            client_id=payload.client_id,
        )

    lot = crear_lot_amb_codi(session, elaboracio.prefix_lot, elaborat_at.date(), _construir)

    for lot_consumit_id in consumits:
        session.add(Consum(lot_produit_id=lot.id, lot_consumit_id=lot_consumit_id, origen=OrigenConsum.automatic))
    session.commit()

    return lot, recepta_incompleta
