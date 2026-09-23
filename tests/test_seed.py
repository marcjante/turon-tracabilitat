"""Regresión: app.models.__init__ debe reexportar todo lo que
app.seed (y cualquier otro módulo) importa desde el paquete, no solo desde
los submódulos — un import roto aquí no lo detectan los tests que importan
directamente de app.models.catalegs/lots/etc."""

from sqlmodel import select

from app.models import Elaboracio, Ingredient, TipusElaboracio
from app.seed import INGREDIENTS, PRODUCTES, SEMIELABORATS, seed


def test_seed_crea_catalegs_i_es_idempotent(session):
    seed(session)
    ingredients = session.exec(select(Ingredient)).all()
    elaboracions = session.exec(select(Elaboracio)).all()
    assert len(ingredients) == len(INGREDIENTS)
    assert len(elaboracions) == len(SEMIELABORATS) + len(PRODUCTES)
    assert all(e.tipus in (TipusElaboracio.semielaborat, TipusElaboracio.producte) for e in elaboracions)

    seed(session)  # segona vegada no ha de duplicar res
    assert len(session.exec(select(Ingredient)).all()) == len(INGREDIENTS)
    assert len(session.exec(select(Elaboracio)).all()) == len(SEMIELABORATS) + len(PRODUCTES)
