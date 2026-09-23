from datetime import date, datetime, timedelta, timezone

from app.models.catalegs import Elaboracio, Ingredient, Proveidor, Recepta, TipusElaboracio
from app.models.lots import Lot, TipusData, TipusLot
from app.models.consums import Consum
from app.schemas.lots import LotEnUsCreate
from app.services.codis import crear_lot_amb_codi
from app.services.lots_en_us import obrir_lot_en_us


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def _crear_ingredient(session, nom="Farina"):
    ingredient = Ingredient(nom=nom)
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


def _crear_proveidor(session, nom="Proveïdor"):
    proveidor = Proveidor(nom=nom)
    session.add(proveidor)
    session.commit()
    session.refresh(proveidor)
    return proveidor


def _crear_lot_materia_primera(session, ingredient_id, codi):
    proveidor = _crear_proveidor(session, nom=f"Prov {codi}")
    lot = Lot(
        tipus=TipusLot.materia_primera,
        codi=codi,
        creat_at=datetime.now(timezone.utc),
        responsable="Anna",
        ingredient_id=ingredient_id,
        proveidor_id=proveidor.id,
        lot_proveidor=codi,
        data_recepcio=date.today(),
        caducitat=date.today() + timedelta(days=30),
        tipus_data=TipusData.caducitat,
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def _obrir(session, ingredient_id, lot_id, inici):
    return obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=ingredient_id, lot_id=lot_id, inici=inici))


def _crear_elaboracio(session, nom, tipus, prefix):
    elaboracio = Elaboracio(nom=nom, tipus=tipus, prefix_lot=prefix)
    session.add(elaboracio)
    session.commit()
    session.refresh(elaboracio)
    return elaboracio


def _crear_recepta_ingredient(session, elaboracio_id, ingredient_id):
    recepta = Recepta(elaboracio_id=elaboracio_id, ingredient_id=ingredient_id)
    session.add(recepta)
    session.commit()


def _crear_recepta_semielaborat(session, elaboracio_id, semielaborat_id):
    recepta = Recepta(elaboracio_id=elaboracio_id, semielaborat_id=semielaborat_id)
    session.add(recepta)
    session.commit()


def _preparar_crema(session, moment):
    """Farina en ús + Crema amb recepta d'un sol ingredient."""
    farina = _crear_ingredient(session, "Farina")
    lot_farina = _crear_lot_materia_primera(session, farina.id, "F-01")
    _obrir(session, farina.id, lot_farina.id, moment - timedelta(hours=1))
    crema = _crear_elaboracio(session, "Crema", TipusElaboracio.semielaborat, "CRE")
    _crear_recepta_ingredient(session, crema.id, farina.id)
    return crema


def test_crear_semielaborat_vincula_lot_obert_i_genera_codi(client, session):
    moment = _utc(2026, 8, 14, 10, 0)
    crema = _preparar_crema(session, moment)

    response = client.post("/semielaborats", json={
        "elaboracio_id": crema.id, "quantitat": 5.0, "unitat": "kg",
        "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["codi"] == "CRE-140826-01"
    assert body["recepta_incompleta"] is False

    from sqlmodel import select
    consums = session.exec(select(Consum).where(Consum.lot_produit_id == body["id"])).all()
    assert len(consums) == 1
    assert consums[0].origen == "automatic"


def test_dues_produccions_mateix_dia_reben_codis_consecutius(client, session):
    """Mandatory: dos cremas del mismo día reciben CRE-140826-01 y -02."""
    moment = _utc(2026, 8, 14, 10, 0)
    crema = _preparar_crema(session, moment)

    codis = []
    for _ in range(2):
        response = client.post("/semielaborats", json={
            "elaboracio_id": crema.id, "quantitat": 5.0, "unitat": "kg",
            "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
        })
        assert response.status_code == 201
        codis.append(response.json()["codi"])

    assert codis == ["CRE-140826-01", "CRE-140826-02"]


def test_crear_semielaborat_sense_lot_obert_retorna_409(client, session):
    farina = _crear_ingredient(session, "Farina")
    crema = _crear_elaboracio(session, "Crema", TipusElaboracio.semielaborat, "CRE")
    _crear_recepta_ingredient(session, crema.id, farina.id)

    response = client.post("/semielaborats", json={
        "elaboracio_id": crema.id, "quantitat": 5.0, "unitat": "kg",
        "elaborat_at": _utc(2026, 1, 1, 10, 0).isoformat(), "torn": "matí", "responsable": "Anna",
    })
    assert response.status_code == 409
    assert "Farina" in response.json()["detail"]


def test_crear_semielaborat_sense_recepta_marca_incompleta(client, session):
    farina = _crear_ingredient(session, "Farina")
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina = _crear_lot_materia_primera(session, farina.id, "F-01")
    _obrir(session, farina.id, lot_farina.id, moment - timedelta(hours=1))
    crema = _crear_elaboracio(session, "Crema", TipusElaboracio.semielaborat, "CRE")
    # sense receta associada

    response = client.post("/semielaborats", json={
        "elaboracio_id": crema.id, "quantitat": 5.0, "unitat": "kg",
        "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["recepta_incompleta"] is True

    from sqlmodel import select
    consums = session.exec(select(Consum).where(Consum.lot_produit_id == body["id"])).all()
    assert len(consums) == 1  # es vincula amb l'únic lot obert existent


def test_crear_producte_requereix_lot_de_cada_semielaborat_de_la_recepta(client, session):
    moment = _utc(2026, 1, 1, 12, 0)
    crema = _preparar_crema(session, moment)
    braços = _crear_elaboracio(session, "Braços", TipusElaboracio.producte, "BRA")
    _crear_recepta_semielaborat(session, braços.id, crema.id)

    lot_crema_response = client.post("/semielaborats", json={
        "elaboracio_id": crema.id, "quantitat": 2.0, "unitat": "kg",
        "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
    })
    lot_crema_id = lot_crema_response.json()["id"]

    sense_lot = client.post("/productes", json={
        "elaboracio_id": braços.id, "quantitat": 10, "unitat": "unitats",
        "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
    })
    assert sense_lot.status_code == 409
    assert "Crema" in sense_lot.json()["detail"]

    amb_lot = client.post("/productes", json={
        "elaboracio_id": braços.id, "quantitat": 10, "unitat": "unitats",
        "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
        "lots_semielaborats": {str(crema.id): lot_crema_id},
    })
    assert amb_lot.status_code == 201
    assert amb_lot.json()["codi"].startswith("BRA-")

    from sqlmodel import select
    consums = session.exec(select(Consum).where(Consum.lot_produit_id == amb_lot.json()["id"])).all()
    assert len(consums) == 1
    assert consums[0].lot_consumit_id == lot_crema_id


def test_crear_producte_amb_lot_semielaborat_invalid_retorna_422(client, session):
    moment = _utc(2026, 1, 1, 12, 0)
    crema = _preparar_crema(session, moment)
    braços = _crear_elaboracio(session, "Braços", TipusElaboracio.producte, "BRA")
    _crear_recepta_semielaborat(session, braços.id, crema.id)

    # Un lot de materia primera (no semielaborat) com a referència invàlida.
    farina_lot = _crear_lot_materia_primera(session, _crear_ingredient(session, "Sucre").id, "SUC-01")

    response = client.post("/productes", json={
        "elaboracio_id": braços.id, "quantitat": 10, "unitat": "unitats",
        "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
        "lots_semielaborats": {str(crema.id): farina_lot.id},
    })
    assert response.status_code == 422


def test_crear_semielaborat_amb_elaboracio_de_tipus_producte_retorna_422(client, session):
    braços = _crear_elaboracio(session, "Braços", TipusElaboracio.producte, "BRA")
    response = client.post("/semielaborats", json={
        "elaboracio_id": braços.id, "quantitat": 1, "unitat": "kg",
        "elaborat_at": _utc(2026, 1, 1, 10, 0).isoformat(), "torn": "matí", "responsable": "Anna",
    })
    assert response.status_code == 422


def test_llistar_semielaborats_i_productes(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    crema = _preparar_crema(session, moment)
    client.post("/semielaborats", json={
        "elaboracio_id": crema.id, "quantitat": 1, "unitat": "kg",
        "elaborat_at": moment.isoformat(), "torn": "matí", "responsable": "Anna",
    })

    response = client.get("/semielaborats")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/productes")
    assert response.status_code == 200
    assert response.json() == []


def test_generacio_de_codi_reintenta_si_hi_ha_colisio(session):
    """Regla 5: si el candidato colisiona (otra fila con ese codi ya
    existe), se reintenta con el siguiente número en vez de fallar."""
    crema = _crear_elaboracio(session, "Crema", TipusElaboracio.semielaborat, "CRE")
    moment_data = date(2026, 8, 14)

    def _construir(codi):
        return Lot(
            tipus=TipusLot.semielaborat, codi=codi, creat_at=datetime.now(timezone.utc),
            responsable="Anna", elaboracio_id=crema.id, quantitat=1, unitat="kg",
            elaborat_at=datetime.now(timezone.utc), torn="matí",
        )

    session.add(_construir("CRE-140826-01"))
    session.commit()

    lot = crear_lot_amb_codi(session, "CRE", moment_data, _construir)
    assert lot.codi == "CRE-140826-02"
