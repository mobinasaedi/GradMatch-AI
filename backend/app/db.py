from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, pool_pre_ping=True, **kwargs)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Additive migrations: (table, column, DDL to run when the column is missing).
# They keep an existing MVP database working without a full migration toolchain.
_ADDITIVE_MIGRATIONS: list[tuple[str, str, str]] = [
    ("students", "user_id", "ALTER TABLE students ADD COLUMN user_id INTEGER REFERENCES users(id)"),
    ("professors", "data_source", "ALTER TABLE professors ADD COLUMN data_source VARCHAR(24) DEFAULT 'openalex'"),
]

_ADDITIVE_INDEXES: list[tuple[str, str]] = [
    ("students", "CREATE INDEX IF NOT EXISTS ix_students_user_id ON students (user_id)"),
]


def run_additive_migrations(target_engine: Engine | None = None) -> list[str]:
    """Add columns/indexes that were introduced after the first release.

    Returns the list of DDL statements that were executed (useful for logs/tests).
    """
    target_engine = target_engine or engine
    inspector = inspect(target_engine)
    tables = set(inspector.get_table_names())
    applied: list[str] = []

    for table, column, ddl in _ADDITIVE_MIGRATIONS:
        if table not in tables:
            continue
        columns = {c["name"] for c in inspector.get_columns(table)}
        if column not in columns:
            with target_engine.begin() as connection:
                connection.execute(text(ddl))
            applied.append(ddl)

    for table, ddl in _ADDITIVE_INDEXES:
        if table in tables:
            with target_engine.begin() as connection:
                connection.execute(text(ddl))

    return applied


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(bind=engine)
    run_additive_migrations(engine)
