"""Initialize database and tables for local development."""
from __future__ import annotations

import sys
from pathlib import Path
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from app.config import get_settings
from app.database import Base
from app import models  # noqa: F401


def ensure_database_exists(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        return

    db_name = url.database
    if not db_name:
        return

    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


def create_tables(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        Base.metadata.create_all(bind=engine)
    finally:
        engine.dispose()


def main() -> None:
    settings = get_settings()
    ensure_database_exists(settings.database_url)
    create_tables(settings.database_url)


if __name__ == "__main__":
    main()
