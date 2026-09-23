"""Engine y sesión de base de datos. DATABASE_URL es SQLite por defecto,
pero no se usa ninguna sintaxis específica de SQLite en el ORM (sí en la
migración inicial, para el índice único parcial — ver ese fichero) para
poder apuntar a PostgreSQL más adelante solo cambiando la URL."""

import os
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, create_engine

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'turon.db'}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_session():
    with Session(engine) as session:
        yield session
