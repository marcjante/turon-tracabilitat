from datetime import date, timedelta

from sqlmodel import select

from app.models.catalegs import Ingredient, Proveidor
from app.models.lots import Lot, TipusLot


def _seed_ingredient_proveidor(session):
    ingredient = Ingredient(nom="Farina")
    proveidor = Proveidor(nom="Molins del Pla")
    session.add(ingredient)
    session.add(proveidor)
    session.commit()
    session.refresh(ingredient)
    session.refresh(proveidor)
    return ingredient, proveidor


def test_crear_entrada_crea_lot_materia_primera(client, session):
    ingredient, proveidor = _seed_ingredient_proveidor(session)
    payload = {
        "ingredient_id": ingredient.id,
        "proveidor_id": proveidor.id,
        "lot_proveidor": "LOT-001",
        "data_recepcio": str(date.today()),
        "caducitat": str(date.today() + timedelta(days=30)),
        "tipus_data": "caducitat",
        "responsable": "Anna",
    }
    response = client.post("/entrades", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["codi"] == "LOT-001"
    assert body["ingredient_id"] == ingredient.id

    lot = session.exec(select(Lot).where(Lot.codi == "LOT-001")).one()
    assert lot.tipus == TipusLot.materia_primera


def test_crear_entrada_codi_duplicat_retorna_409(client, session):
    ingredient, proveidor = _seed_ingredient_proveidor(session)
    payload = {
        "ingredient_id": ingredient.id,
        "proveidor_id": proveidor.id,
        "lot_proveidor": "LOT-DUP",
        "data_recepcio": str(date.today()),
        "caducitat": str(date.today() + timedelta(days=30)),
        "tipus_data": "caducitat",
        "responsable": "Anna",
    }
    first = client.post("/entrades", json=payload)
    assert first.status_code == 201
    second = client.post("/entrades", json=payload)
    assert second.status_code == 409


def test_crear_entrada_amb_client_id_repetit_es_idempotent(client, session):
    """Fase 4 (offline): reenviar la mateixa creació (mateix client_id)
    no ha de duplicar el lot — simula un dispositiu que reintenta
    perquè va perdre la resposta en un tall de xarxa."""
    ingredient, proveidor = _seed_ingredient_proveidor(session)
    payload = {
        "ingredient_id": ingredient.id,
        "proveidor_id": proveidor.id,
        "lot_proveidor": "LOT-OFFLINE",
        "data_recepcio": str(date.today()),
        "caducitat": str(date.today() + timedelta(days=30)),
        "tipus_data": "caducitat",
        "responsable": "Anna",
        "client_id": "11111111-1111-1111-1111-111111111111",
    }
    first = client.post("/entrades", json=payload)
    assert first.status_code == 201
    second = client.post("/entrades", json=payload)
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    tots = session.exec(select(Lot).where(Lot.codi == "LOT-OFFLINE")).all()
    assert len(tots) == 1


def test_llistar_entrades_filtra_per_ingredient(client, session):
    farina, proveidor = _seed_ingredient_proveidor(session)
    sucre = Ingredient(nom="Sucre")
    session.add(sucre)
    session.commit()
    session.refresh(sucre)

    for ingredient_id, codi in ((farina.id, "F-01"), (sucre.id, "S-01")):
        client.post("/entrades", json={
            "ingredient_id": ingredient_id, "proveidor_id": proveidor.id, "lot_proveidor": codi,
            "data_recepcio": str(date.today()), "caducitat": str(date.today() + timedelta(days=10)),
            "tipus_data": "caducitat", "responsable": "Anna",
        })

    response = client.get(f"/entrades?ingredient_id={farina.id}")
    assert response.status_code == 200
    codis = [row["codi"] for row in response.json()]
    assert codis == ["F-01"]


def test_llistar_entrades_filtra_per_caduca_en_dies(client, session):
    ingredient, proveidor = _seed_ingredient_proveidor(session)
    client.post("/entrades", json={
        "ingredient_id": ingredient.id, "proveidor_id": proveidor.id, "lot_proveidor": "AVIAT",
        "data_recepcio": str(date.today()), "caducitat": str(date.today() + timedelta(days=2)),
        "tipus_data": "caducitat", "responsable": "Anna",
    })
    client.post("/entrades", json={
        "ingredient_id": ingredient.id, "proveidor_id": proveidor.id, "lot_proveidor": "LLUNY",
        "data_recepcio": str(date.today()), "caducitat": str(date.today() + timedelta(days=60)),
        "tipus_data": "caducitat", "responsable": "Anna",
    })

    response = client.get("/entrades?caduca_en_dies=5")
    codis = [row["codi"] for row in response.json()]
    assert codis == ["AVIAT"]
