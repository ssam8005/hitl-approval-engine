"""
database/connection.py — SQLite engine and session factory.

Uses WAL (Write-Ahead Logging) mode for SQLite so reads don't block writes
during high-concurrency approval processing.
Swap DATABASE_URL to postgresql://... for production — zero code changes needed.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from database.models import Base

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from config import get_settings
        cfg = get_settings()
        connect_args = {}
        if cfg.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(cfg.database_url, connect_args=connect_args)
        if cfg.database_url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_wal(dbapi_conn, _):
                dbapi_conn.execute("PRAGMA journal_mode=WAL")
    return _engine


def init_db():
    """Create all tables. Safe to call multiple times."""
    Base.metadata.create_all(bind=_get_engine())


def get_db():
    """FastAPI dependency: yield a database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
