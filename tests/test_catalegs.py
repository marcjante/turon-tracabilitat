def test_crear_i_llistar_ingredient(client):
    response = client.post("/ingredients", json={"nom": "Farina"})
    assert response.status_code == 201
    assert response.json()["actiu"] is True

    response = client.get("/ingredients")
    assert response.status_code == 200
    assert [i["nom"] for i in response.json()] == ["Farina"]


def test_ingredient_nom_duplicat_retorna_409(client):
    client.post("/ingredients", json={"nom": "Farina"})
    response = client.post("/ingredients", json={"nom": "Farina"})
    assert response.status_code == 409


def test_actualitzar_ingredient_parcial(client):
    ingredient = client.post("/ingredients", json={"nom": "Farina"}).json()
    response = client.patch(f"/ingredients/{ingredient['id']}", json={"actiu": False})
    assert response.status_code == 200
    assert response.json()["actiu"] is False
    assert response.json()["nom"] == "Farina"


def test_eliminar_ingredient(client):
    ingredient = client.post("/ingredients", json={"nom": "Farina"}).json()
    response = client.delete(f"/ingredients/{ingredient['id']}")
    assert response.status_code == 204
    assert client.get(f"/ingredients/{ingredient['id']}").status_code == 404


def test_crear_elaboracio(client):
    response = client.post("/elaboracions", json={"nom": "Crema", "tipus": "semielaborat", "prefix_lot": "CRE"})
    assert response.status_code == 201
    assert response.json()["tipus"] == "semielaborat"


def test_recepta_exigeix_exactament_un_component(client):
    elaboracio = client.post("/elaboracions", json={"nom": "Braços", "tipus": "producte", "prefix_lot": "BRA"}).json()
    ingredient = client.post("/ingredients", json={"nom": "Farina"}).json()

    cap = client.post("/receptes", json={"elaboracio_id": elaboracio["id"]})
    assert cap.status_code == 422

    tots_dos = client.post("/receptes", json={
        "elaboracio_id": elaboracio["id"], "ingredient_id": ingredient["id"], "semielaborat_id": elaboracio["id"],
    })
    assert tots_dos.status_code == 422

    valida = client.post("/receptes", json={"elaboracio_id": elaboracio["id"], "ingredient_id": ingredient["id"]})
    assert valida.status_code == 201


def test_recepta_component_duplicat_retorna_409(client):
    elaboracio = client.post("/elaboracions", json={"nom": "Braços", "tipus": "producte", "prefix_lot": "BRA"}).json()
    ingredient = client.post("/ingredients", json={"nom": "Farina"}).json()
    payload = {"elaboracio_id": elaboracio["id"], "ingredient_id": ingredient["id"]}

    assert client.post("/receptes", json=payload).status_code == 201
    assert client.post("/receptes", json=payload).status_code == 409
