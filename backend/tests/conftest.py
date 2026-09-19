from pathlib import Path

import pytest
from sqlmodel import create_engine

from app.adapters.outbound.repository.db import create_db_and_tables
from app.adapters.outbound.repository.project_repository import SqlProjectRepository


@pytest.fixture()
def repository(tmp_path: Path) -> SqlProjectRepository:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    create_db_and_tables(engine)
    return SqlProjectRepository(engine)
