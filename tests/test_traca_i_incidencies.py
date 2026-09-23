from datetime import date, datetime, timedelta, timezone

from app.models.catalegs import Elaboracio, Ingredient, Proveidor, TipusElaboracio
from app.models.consums import Consum, OrigenConsum
from app.models.lots import Lot, TipusData, TipusLot
from app.schemas.lots import LotEnUsCreate
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
        tipus=TipusLot.materia_primera, codi=codi, creat_at=datetime.now(timezone.utc), responsable="Anna",
        ingredient_id=ingredient_id, proveidor_id=proveidor.id, lot_proveidor=codi,
        data_recepcio=date.today(), caducitat=date.today() + timedelta(days=30), tipus_data=TipusData.caducitat,
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def _crear_elaboracio(session, nom, tipus, prefix):
    elaboracio = Elaboracio(nom=nom, tipus=tipus, prefix_lot=prefix)
    session.add(elaboracio)
    session.commit()
    session.refresh(elaboracio)
    return elaboracio


def _crear_lot_elaboracio(session, elaboracio, codi, moment):
    lot = Lot(
        tipus=TipusLot(elaboracio.tipus.value), codi=codi, creat_at=datetime.now(timezone.utc),
        responsable="Anna", elaboracio_id=elaboracio.id, quantitat=1.0, unitat="kg",
        elaborat_at=moment, torn="matí",
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot


def _crear_consum(session, lot_produit_id, lot_consumit_id, origen=OrigenConsum.automatic):
    session.add(Consum(lot_produit_id=lot_produit_id, lot_consumit_id=lot_consumit_id, origen=origen))
    session.commit()


def _cadena_farina_planxes_braços(session, moment):
    """farina -> planxes -> braços, la cadena que usa el test mandatorio."""
    farina = _crear_ingredient(session, "Farina")
    lot_farina = _crear_lot_materia_primera(session, farina.id, "F-01")
    obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=farina.id, lot_id=lot_farina.id, inici=moment - timedelta(hours=2)))

    planxes = _crear_elaboracio(session, "Planxes", TipusElaboracio.semielaborat, "PLA")
    lot_planxes = _crear_lot_elaboracio(session, planxes, "PLA-01", moment)
    _crear_consum(session, lot_planxes.id, lot_farina.id)

    braços = _crear_elaboracio(session, "Braços", TipusElaboracio.producte, "BRA")
    lot_braços = _crear_lot_elaboracio(session, braços, "BRA-01", moment)
    _crear_consum(session, lot_braços.id, lot_planxes.id)

    return lot_farina, lot_planxes, lot_braços


def test_traca_endavant_recorre_tres_nivells(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, lot_planxes, lot_braços = _cadena_farina_planxes_braços(session, moment)

    response = client.get(f"/traca/endavant/{lot_farina.id}")
    assert response.status_code == 200
    body = response.json()
    assert [item["codi"] for item in body["semielaborat"]] == ["PLA-01"]
    assert [item["codi"] for item in body["producte"]] == ["BRA-01"]
    assert body["materia_primera"] == []


def test_traca_enrere_arriba_del_producte_al_lot_de_proveidor(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, lot_planxes, lot_braços = _cadena_farina_planxes_braços(session, moment)

    response = client.get(f"/traca/enrere/{lot_braços.id}")
    assert response.status_code == 200
    body = response.json()
    assert [item["codi"] for item in body["materia_primera"]] == ["F-01"]
    assert [item["codi"] for item in body["semielaborat"]] == ["PLA-01"]
    assert body["producte"] == []


def test_traca_lot_inexistent_retorna_404(client):
    response = client.get("/traca/endavant/9999")
    assert response.status_code == 404


def test_traca_exclou_consums_anulats(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, lot_planxes, _ = _cadena_farina_planxes_braços(session, moment)

    response = client.delete(f"/lots/{lot_planxes.id}/consums?lot_consumit_id={lot_farina.id}")
    assert response.status_code == 200

    resultat = client.get(f"/traca/endavant/{lot_farina.id}").json()
    assert resultat["semielaborat"] == []
    assert resultat["producte"] == []


def test_incidencia_guarda_snapshot_dels_afectats(client, session):
    """Mandatory: una incidencia guarda el snapshot de afectados."""
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, lot_planxes, lot_braços = _cadena_farina_planxes_braços(session, moment)

    response = client.post("/incidencies", json={
        "tipus": "alerta", "responsable": "Anna", "lot_afectat_id": lot_farina.id,
        "motiu": "Possible contaminació creuada",
    })
    assert response.status_code == 201
    body = response.json()
    assert [i["codi"] for i in body["afectats_snapshot"]["semielaborat"]] == ["PLA-01"]
    assert [i["codi"] for i in body["afectats_snapshot"]["producte"]] == ["BRA-01"]


def test_incidencia_requereix_lot_afectat_existent(client):
    response = client.post("/incidencies", json={
        "tipus": "alerta", "responsable": "Anna", "lot_afectat_id": 9999, "motiu": "x",
    })
    assert response.status_code == 404


def test_llistar_incidencies_filtra_per_lot(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, _, _ = _cadena_farina_planxes_braços(session, moment)
    client.post("/incidencies", json={
        "tipus": "alerta", "responsable": "Anna", "lot_afectat_id": lot_farina.id, "motiu": "x",
    })

    response = client.get(f"/incidencies?lot_afectat_id={lot_farina.id}")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_anular_lot_no_el_borra_i_lexclou_de_les_consultes(client, session):
    """Mandatory: anular un lote no lo borra y lo excluye de las consultas."""
    farina = _crear_ingredient(session, "Farina")
    lot_vell = _crear_lot_materia_primera(session, farina.id, "F-ERRONI")
    lot_nou = _crear_lot_materia_primera(session, farina.id, "F-CORRECTE")

    response = client.post(f"/lots/{lot_vell.id}/anular", json={"lot_nou_id": lot_nou.id, "motiu": "codi mal escrit"})
    assert response.status_code == 200
    assert response.json()["anulat_per_id"] == lot_nou.id

    # No s'ha esborrat: encara es pot cercar explícitament per codi...
    cercat = client.get("/lots/cerca?codi=F-ERRONI")
    assert cercat.status_code == 200
    assert cercat.json() == []  # ...però queda exclòs de les consultes normals

    entrades = client.get(f"/entrades?ingredient_id={farina.id}")
    codis = [e["codi"] for e in entrades.json()]
    assert "F-ERRONI" not in codis
    assert "F-CORRECTE" in codis


def test_obtenir_lot_per_id_inclou_anulats(client, session):
    """A diferencia de /entrades i /lots/cerca, l'endpoint per id ha de
    poder resoldre un lot encara que estigui anul·lat (necessari per
    mostrar el codi d'un lot referenciat des d'una incidència)."""
    farina = _crear_ingredient(session, "Farina")
    lot_vell = _crear_lot_materia_primera(session, farina.id, "F-ERRONI")
    lot_nou = _crear_lot_materia_primera(session, farina.id, "F-CORRECTE")
    client.post(f"/lots/{lot_vell.id}/anular", json={"lot_nou_id": lot_nou.id})

    response = client.get(f"/lots/{lot_vell.id}")
    assert response.status_code == 200
    assert response.json()["codi"] == "F-ERRONI"
    assert response.json()["anulat_per_id"] == lot_nou.id


def test_obtenir_lot_inexistent_retorna_404(client, session):
    response = client.get("/lots/999999")
    assert response.status_code == 404


def test_anular_lot_amb_tipus_diferent_retorna_422(client, session):
    farina = _crear_ingredient(session, "Farina")
    lot_materia = _crear_lot_materia_primera(session, farina.id, "F-01")
    crema = _crear_elaboracio(session, "Crema", TipusElaboracio.semielaborat, "CRE")
    lot_crema = _crear_lot_elaboracio(session, crema, "CRE-010126-01", _utc(2026, 1, 1, 10, 0))

    response = client.post(f"/lots/{lot_materia.id}/anular", json={"lot_nou_id": lot_crema.id})
    assert response.status_code == 422


def test_anular_lot_ja_anulat_retorna_409(client, session):
    farina = _crear_ingredient(session, "Farina")
    lot_a = _crear_lot_materia_primera(session, farina.id, "A")
    lot_b = _crear_lot_materia_primera(session, farina.id, "B")
    lot_c = _crear_lot_materia_primera(session, farina.id, "C")

    client.post(f"/lots/{lot_a.id}/anular", json={"lot_nou_id": lot_b.id})
    response = client.post(f"/lots/{lot_a.id}/anular", json={"lot_nou_id": lot_c.id})
    assert response.status_code == 409


def test_cercar_lot_per_codi_parcial(client, session):
    farina = _crear_ingredient(session, "Farina")
    _crear_lot_materia_primera(session, farina.id, "F-2026-08-14")

    response = client.get("/lots/cerca?codi=2026-08")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_afegir_segon_consum_mateix_ingredient_crea_incidencia_canvi_lot(client, session):
    """Regla 4: consumir dos lotes del mismo ingrediente (cambio de lote a
    mitad de turno) crea automáticamente una incidencia canvi_lot."""
    moment = _utc(2026, 1, 1, 10, 0)
    farina = _crear_ingredient(session, "Farina")
    lot_farina_1 = _crear_lot_materia_primera(session, farina.id, "F-01")
    lot_farina_2 = _crear_lot_materia_primera(session, farina.id, "F-02")
    obrir_lot_en_us(session, LotEnUsCreate(ingredient_id=farina.id, lot_id=lot_farina_1.id, inici=moment - timedelta(hours=2)))

    # No cal recepta aquí: el consum es dona d'alta a mà, directament.
    crema = _crear_elaboracio(session, "Crema", TipusElaboracio.semielaborat, "CRE")
    lot_crema = _crear_lot_elaboracio(session, crema, "CRE-010126-01", moment)
    _crear_consum(session, lot_crema.id, lot_farina_1.id)

    response = client.post(f"/lots/{lot_crema.id}/consums", json={
        "lot_consumit_id": lot_farina_2.id, "responsable": "Anna",
    })
    assert response.status_code == 201

    incidencies = client.get(f"/incidencies?lot_afectat_id={lot_crema.id}").json()
    assert len(incidencies) == 1
    assert incidencies[0]["tipus"] == "canvi_lot"
    assert incidencies[0]["lot_anterior_id"] == lot_farina_1.id
    assert incidencies[0]["lot_nou_id"] == lot_farina_2.id


def test_afegir_consum_duplicat_retorna_409(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, lot_planxes, _ = _cadena_farina_planxes_braços(session, moment)

    response = client.post(f"/lots/{lot_planxes.id}/consums", json={
        "lot_consumit_id": lot_farina.id, "responsable": "Anna",
    })
    assert response.status_code == 409


def test_eliminar_consum_marca_anulat_at_no_esborra(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, lot_planxes, _ = _cadena_farina_planxes_braços(session, moment)

    response = client.delete(f"/lots/{lot_planxes.id}/consums?lot_consumit_id={lot_farina.id}")
    assert response.status_code == 200
    assert response.json()["anulat_at"] is not None

    from sqlmodel import select
    fila = session.exec(
        select(Consum).where(Consum.lot_produit_id == lot_planxes.id, Consum.lot_consumit_id == lot_farina.id)
    ).one()
    assert fila is not None  # la fila segueix existint


def test_eliminar_consum_ja_anulat_retorna_409(client, session):
    moment = _utc(2026, 1, 1, 10, 0)
    lot_farina, lot_planxes, _ = _cadena_farina_planxes_braços(session, moment)
    client.delete(f"/lots/{lot_planxes.id}/consums?lot_consumit_id={lot_farina.id}")

    response = client.delete(f"/lots/{lot_planxes.id}/consums?lot_consumit_id={lot_farina.id}")
    assert response.status_code == 409
