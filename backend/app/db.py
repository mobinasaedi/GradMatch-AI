from collections.abc import Iterator

from sqlalchemy import create_engine
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


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(bind=engine)
    # Additive migration for existing MVP SQLite/PostgreSQL databases. Existing
    # anonymous student rows remain unowned and are never exposed to new accounts.
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "students" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("students")}
        if "user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE students ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            with engine.begin() as connection:
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_students_user_id ON students (user_id)"))
