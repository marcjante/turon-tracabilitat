"""Cada test corre contra una base SQLite nueva (fichero temporal, no en
memoria: así el pragma foreign_keys y los índices parciales se comportan
exactamente igual que en producción). Usa SQLModel.metadata.create_all —
no Alembic — pero el modelo y la migración 0001 están verificados como
idénticos (ver `uv run alembic check`), así que esto no diverge de lo que
levantaría `alembic upgrade head`."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")  # sobrescrito por engine de test igualmente

import app.models  # noqa: E402  — registra las tablas en SQLModel.metadata
from app.db import get_session  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture()
def engine():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(test_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()
    os.unlink(path)


@pytest.fixture()
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture()
def client(engine):
    def _get_session_override():
        with Session(engine) as s:
            yield s

    fastapi_app.dependency_overrides[get_session] = _get_session_override
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
