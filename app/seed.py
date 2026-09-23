"""Datos iniciales de catálogo (ingredientes y elaboraciones), según las
fichas de trazabilidad. Idempotente: no duplica filas si ya existen.

Uso: uv run python -m app.seed
"""

from sqlmodel import Session, select

from app.db import engine
from app.models import Elaboracio, Ingredient, TipusElaboracio

INGREDIENTS = [
    "Farina",
    "Sucre",
    "Ou / ovoproducte",
    "Mantega / greix",
    "Llet / nata",
    "Xocolata / cacau",
    "Fruits secs",
    "Gelatina / estabilitzant",
]

SEMIELABORATS = [
    ("Pa de pessic", "PPE"),
    ("Planxes", "PLA"),
    ("Yema", "YEM"),
    ("Crema", "CRE"),
    ("Trufa", "TRU"),
    ("Bany", "BAN"),
]

PRODUCTES = [
    ("Melindros", "MEL"),
    ("Magdalenes", "MAG"),
    ("Carquinyolis", "CAR"),
    ("Pastissos", "PST"),
    ("Braços", "BRA"),
    ("Mousses", "MOU"),
]


def seed(session: Session) -> None:
    existing_ingredients = {i.nom for i in session.exec(select(Ingredient)).all()}
    for nom in INGREDIENTS:
        if nom not in existing_ingredients:
            session.add(Ingredient(nom=nom))

    existing_elaboracions = {e.nom for e in session.exec(select(Elaboracio)).all()}
    for nom, prefix in SEMIELABORATS:
        if nom not in existing_elaboracions:
            session.add(Elaboracio(nom=nom, tipus=TipusElaboracio.semielaborat, prefix_lot=prefix))
    for nom, prefix in PRODUCTES:
        if nom not in existing_elaboracions:
            session.add(Elaboracio(nom=nom, tipus=TipusElaboracio.producte, prefix_lot=prefix))

    session.commit()


if __name__ == "__main__":
    with Session(engine) as session:
        seed(session)
    print("Seed completado.")
