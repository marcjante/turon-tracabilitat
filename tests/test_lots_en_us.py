from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.catalegs import Ingredient, Proveidor
from app.models.lots import Lot, LotEnUs, TipusData, TipusLot
from app.schemas.lots import LotEnUsCreate
from app.services.lots_en_us import lot_obert_per_ingredient, obrir_lot_en_us, tancar_lot_en_us


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def _crear_ingredient(session, nom="Farina"):
    ingredient = Ingredient(nom=nom)
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


def _crear_proveidor(session, nom="Proveïdor de prova"):
    proveidor = Proveidor(nom=nom)
    session.add(proveidor)
    session.commit()
    session.refresh(proveidor)
    return proveidor


def _crear_lot_materia_primera(session, ingredient_id, codi, caducitat=None, creat_at=None):
    lot = Lot(
        tipus=TipusLot.materia_primera,
        codi=codi,
        creat_at=creat_at or datetime.now(timezone.utc),
        responsable="Anna",
        ingredient_id=ingredient_id,
        proveidor_id=_crear_proveidor(session, nom=f"Proveïdor {codi}").id,
        lot_proveidor=codi,
        data_recepcio=date.today(),
        caducitat=caducitat or (date.today() + timedelta(days=30)),
        tipus_data=TipusData.caducitat,
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def test_obrir_lot_tanca_el_lot_anterior_del_mateix_ingredient(session):
    ingredient = _crear_ingredient(session)
    lot_a = _crear_lot_materia_primera(session, ingredient.id, "A")
    lot_b = _crear_lot_materia_primera(session, ingredient.id, "B")

    primer = obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot_a.id, inici=_utc(2026, 1, 1, 9, 0)))
    assert primer.fi is None

    segon = obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot_b.id, inici=_utc(2026, 1, 1, 11, 0)))

    session.refresh(primer)
    assert primer.fi == _utc(2026, 1, 1, 11, 0)
    assert segon.fi is None


def test_no_poden_haver_dos_lots_oberts_del_mateix_ingredient(session):
    ingredient = _crear_ingredient(session)
    lot_a = _crear_lot_materia_primera(session, ingredient.id, "A")
    lot_b = _crear_lot_materia_primera(session, ingredient.id, "B")

    obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot_a.id, inici=_utc(2026, 1, 1, 9, 0)))
    obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot_b.id, inici=_utc(2026, 1, 1, 11, 0)))

    from sqlmodel import select

    oberts = session.exec(select(LotEnUs).where(LotEnUs.ingredient_id == ingredient.id, LotEnUs.fi.is_(None))).all()
    assert len(oberts) == 1

    # El índice único parcial también protege a nivel de base de datos,
    # no solo por la lógica del servicio: forzar una segunda fila con
    # fi IS NULL directamente debe fallar.
    session.add(LotEnUs(ingredient_id=ingredient.id, lot_id=lot_a.id, inici=_utc(2026, 1, 1, 12, 0)))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_obrir_lot_caducat_retorna_422(client, session):
    ingredient = _crear_ingredient(session)
    lot = _crear_lot_materia_primera(session, ingredient.id, "CADUCAT", caducitat=date.today() - timedelta(days=1))

    response = client.post("/lots-en-us", json={
        "ingredient_id": ingredient.id, "lot_id": lot.id, "inici": datetime.now(timezone.utc).isoformat(),
    })
    assert response.status_code == 422


def test_obrir_lot_dun_altre_ingredient_retorna_422(client, session):
    farina = _crear_ingredient(session, "Farina")
    sucre = _crear_ingredient(session, "Sucre")
    lot_farina = _crear_lot_materia_primera(session, farina.id, "F-01")

    response = client.post("/lots-en-us", json={
        "ingredient_id": sucre.id, "lot_id": lot_farina.id, "inici": datetime.now(timezone.utc).isoformat(),
    })
    assert response.status_code == 422


def test_tancar_lot_en_us_sense_obrir_un_de_nou(session):
    ingredient = _crear_ingredient(session)
    lot = _crear_lot_materia_primera(session, ingredient.id, "A")
    obert = obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot.id, inici=_utc(2026, 1, 1, 9, 0)))

    tancat = tancar_lot_en_us(session, obert.id, _utc(2026, 1, 2, 8, 0))
    assert tancat.fi == _utc(2026, 1, 2, 8, 0)


def test_obrir_lot_amb_client_id_repetit_es_idempotent(session):
    """Fase 5 (offline): reenviar el mateix client_id no ha de tancar
    dues vegades l'anterior ni obrir dos registres nous."""
    ingredient = _crear_ingredient(session)
    lot_a = _crear_lot_materia_primera(session, ingredient.id, "A")
    lot_b = _crear_lot_materia_primera(session, ingredient.id, "B")

    obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot_a.id, inici=_utc(2026, 1, 1, 9, 0)))
    payload = LotEnUsCreate(
        ingredient_id=ingredient.id, lot_id=lot_b.id, inici=_utc(2026, 1, 1, 11, 0),
        client_id="22222222-2222-2222-2222-222222222222",
    )
    primer = obrir_lot_en_us(session, payload)
    segon = obrir_lot_en_us(session, payload)
    assert primer.id == segon.id

    from sqlmodel import select
    tots = session.exec(select(LotEnUs).where(LotEnUs.lot_id == lot_b.id)).all()
    assert len(tots) == 1


def test_tancar_lot_amb_mateix_fi_es_idempotent(session):
    """Fase 5 (offline): reenviar el mateix tancament (mateix fi) no ha
    de retornar 409 — és un reintent, no un conflicte real."""
    ingredient = _crear_ingredient(session)
    lot = _crear_lot_materia_primera(session, ingredient.id, "A")
    obert = obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot.id, inici=_utc(2026, 1, 1, 9, 0)))

    primer = tancar_lot_en_us(session, obert.id, _utc(2026, 1, 2, 8, 0))
    segon = tancar_lot_en_us(session, obert.id, _utc(2026, 1, 2, 8, 0))
    assert primer.fi == segon.fi == _utc(2026, 1, 2, 8, 0)


def test_tancar_lot_ja_tancat_retorna_409(client, session):
    ingredient = _crear_ingredient(session)
    lot = _crear_lot_materia_primera(session, ingredient.id, "A")
    obert = obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot.id, inici=_utc(2026, 1, 1, 9, 0)))
    tancar_lot_en_us(session, obert.id, _utc(2026, 1, 2, 8, 0))

    response = client.post(f"/lots-en-us/{obert.id}/tancar", json={"fi": "2026-01-03T00:00:00"})
    assert response.status_code == 409


def test_lot_obert_per_ingredient_respecta_la_hora_exacta(session):
    """Mandatory: un semielaborado a las 10:00 se vincula con el lote
    abierto a las 10:00, no con el que se abre a las 11:00."""
    ingredient = _crear_ingredient(session)
    lot_a = _crear_lot_materia_primera(session, ingredient.id, "A")
    lot_b = _crear_lot_materia_primera(session, ingredient.id, "B")

    obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot_a.id, inici=_utc(2026, 1, 1, 8, 0)))
    obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient.id, lot_id=lot_b.id, inici=_utc(2026, 1, 1, 11, 0)))

    a_les_10 = lot_obert_per_ingredient(session, ingredient.id, _utc(2026, 1, 1, 10, 0))
    assert a_les_10.lot_id == lot_a.id

    a_les_11_30 = lot_obert_per_ingredient(session, ingredient.id, _utc(2026, 1, 1, 11, 30))
    assert a_les_11_30.lot_id == lot_b.id


def test_lots_en_us_routes_end_to_end(client, session):
    ingredient = _crear_ingredient(session)
    lot = _crear_lot_materia_primera(session, ingredient.id, "A")

    obert = client.post("/lots-en-us", json={
        "ingredient_id": ingredient.id, "lot_id": lot.id, "inici": "2026-01-01T09:00:00",
    })
    assert obert.status_code == 201

    oberts = client.get("/lots-en-us")
    assert oberts.status_code == 200 and len(oberts.json()) == 1

    historial = client.get("/lots-en-us/historial")
    assert historial.status_code == 200 and len(historial.json()) == 1
