"""Ficha 2 — lotes de materia prima en uso.

Regla de negocio 1: al abrir un lote en uso, en la misma transacción se
cierra (fi = inici del nuevo) el lote abierto del mismo ingrediente y se
abre el nuevo. Si el lote de materia prima está caducado, 422.

Conflicto entre dispositivos (fase 8 offline): dos tablets pueden abrir
un lote en uso del mismo ingrediente estando ambas sin conexión; el
orden en que sus peticiones llegan al sincronizar no tiene por qué
coincidir con el orden real de sus `inici`. obrir_lot_en_us() no asume
que "el que llega ahora es el más reciente" — busca su predecesor y
sucesor real por `inici` entre los registros ya existentes de ese
ingrediente y se inserta en el punto correcto de la línia de tiempo,
así que el resultado final converge igual sea cual sea el orden de
llegada (ver test_dos_dispositius_offline_obren_en_ordre_invers)."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.lots import Lot, LotEnUs, TipusLot
from app.schemas.lots import LotEnUsCreate


def _lot_materia_primera_o_404(session: Session, lot_id: int, ingredient_id: int) -> Lot:
    lot = session.get(Lot, lot_id)
    if lot is None or lot.tipus != TipusLot.materia_primera or lot.anulat_per_id is not None:
        raise HTTPException(status_code=404, detail="lote de materia prima no encontrado")
    if lot.ingredient_id != ingredient_id:
        raise HTTPException(status_code=422, detail="el lote no pertenece a este ingrediente")
    return lot


def obrir_lot_en_us(session: Session, payload: LotEnUsCreate) -> LotEnUs:
    # Idempotència (fase 5 offline): si ja s'ha processat aquest
    # client_id, es retorna el registre existent SENSE repetir l'efecte
    # secundari de tancar l'anterior obert — repetir-lo tancaria un
    # lot en ús que un altre dispositiu ja hagi obert de nou mentrestant.
    if payload.client_id is not None:
        existent = session.exec(select(LotEnUs).where(LotEnUs.client_id == payload.client_id)).first()
        if existent is not None:
            return existent

    inici = payload.inici or datetime.now(timezone.utc)
    lot = _lot_materia_primera_o_404(session, payload.lot_id, payload.ingredient_id)

    if lot.caducitat is not None and lot.caducitat < inici.date():
        raise HTTPException(status_code=422, detail=f"el lote {lot.codi} está caducado ({lot.caducitat})")

    # Predecessor real: el registre d'aquest ingredient amb l'`inici` més
    # gran que no sigui posterior al nostre. Si encara estava obert
    # (fi IS NULL), l'hem de tancar ara — però només en aquest cas; si ja
    # estava tancat (per un `tancar_lot_en_us` manual, o perquè un altre
    # registre posterior ja el va tancar), no el toquem.
    anterior = session.exec(
        select(LotEnUs)
        .where(LotEnUs.ingredient_id == payload.ingredient_id, LotEnUs.inici <= inici)
        .order_by(LotEnUs.inici.desc())
    ).first()
    if anterior is not None and anterior.fi is None:
        anterior.fi = inici
        session.add(anterior)

    # Successor real: el registre amb l'`inici` més petit que sigui
    # posterior al nostre. Si n'hi ha un, el nostre `fi` és el seu
    # `inici` (encara que hagi arribat abans que nosaltres al servidor).
    successor = session.exec(
        select(LotEnUs)
        .where(LotEnUs.ingredient_id == payload.ingredient_id, LotEnUs.inici > inici)
        .order_by(LotEnUs.inici.asc())
    ).first()

    nou = LotEnUs(
        ingredient_id=payload.ingredient_id,
        lot_id=payload.lot_id,
        inici=inici,
        fi=successor.inici if successor is not None else None,
        observacions=payload.observacions,
        client_id=payload.client_id,
    )
    session.add(nou)
    session.commit()
    session.refresh(nou)
    return nou


def tancar_lot_en_us(session: Session, lot_en_us_id: int, fi: datetime) -> LotEnUs:
    """Cierra un lote en uso sin abrir uno nuevo (se acaba y todavía no
    hay sustituto).

    Idempotente por estado, no por client_id: si ya estaba cerrado con
    ese mismo fi (hasta el segundo), un reintento offline devuelve el
    registro tal cual en vez de 409 — necesario porque un dispositivo
    puede reenviar el cierre si perdió la respuesta original."""
    registre = session.get(LotEnUs, lot_en_us_id)
    if registre is None:
        raise HTTPException(status_code=404, detail="registro de lote en uso no encontrado")
    if registre.fi is not None:
        if registre.fi == fi:
            return registre
        raise HTTPException(status_code=409, detail="este lote en uso ya estaba cerrado")
    registre.fi = fi
    session.add(registre)
    session.commit()
    session.refresh(registre)
    return registre


def lot_obert_per_ingredient(session: Session, ingredient_id: int, en: datetime) -> LotEnUs | None:
    """El lote en uso vigente para un ingrediente en un instante dado —
    usado por services/semielaborats.py y services/productes.py (Fase 2)
    para la vinculación automática."""
    return session.exec(
        select(LotEnUs).where(
            LotEnUs.ingredient_id == ingredient_id,
            LotEnUs.inici <= en,
            (LotEnUs.fi.is_(None)) | (LotEnUs.fi > en),
        )
    ).first()


def llistar_lots_en_us(session: Session) -> list[LotEnUs]:
    return list(session.exec(select(LotEnUs).where(LotEnUs.fi.is_(None)).order_by(LotEnUs.inici.desc())).all())


def llistar_historial(session: Session, ingredient_id: int | None = None) -> list[LotEnUs]:
    query = select(LotEnUs)
    if ingredient_id is not None:
        query = query.where(LotEnUs.ingredient_id == ingredient_id)
    return list(session.exec(query.order_by(LotEnUs.inici.desc())).all())
