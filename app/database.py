"""Camada de acesso ao banco (SQLAlchemy 2.0 + SQLite).

Usa scoped_session para que cada request tenha sua sessao, e um teardown no
app fecha a sessao ao fim de cada request. O schema e criado no boot via
create_all.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from .config import Config

# check_same_thread=False permite que o SQLite seja usado por threads diferentes
# (o servidor dev do Flask e o gunicorn com workers usam threads).
_connect_args = (
    {"check_same_thread": False}
    if Config.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    Config.DATABASE_URL,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)

Base = declarative_base()


def init_db() -> None:
    """Cria todas as tabelas se ainda nao existirem."""
    from . import models  # noqa: F401  (garante o registro dos modelos)

    Base.metadata.create_all(bind=engine)
