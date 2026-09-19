"""Motor SQLite + fabrica de sesiones. Un archivo por workspace (ver
config/settings.py) -- suficiente para una app local mono-usuario (seccion 10
del doc de arquitectura)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config.settings import Settings


def make_engine(settings: Settings):
    url = f"sqlite:///{settings.db_path}"
    return create_engine(url, connect_args={"check_same_thread": False})


def create_db_and_tables(engine) -> None:
    # Importar los modelos antes de create_all para que queden registrados
    # en SQLModel.metadata -- sin este import, una app que solo importa
    # db.py (sin tocar models.py directamente) creceria un esquema vacio.
    from app.adapters.outbound.repository import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(engine) -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
