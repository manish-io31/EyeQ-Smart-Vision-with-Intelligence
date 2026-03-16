"""
EYEQ – Database Engine & Session Factory

Supports SQLite (dev) and PostgreSQL (prod) via SQLAlchemy.
Switch between them by changing DATABASE_URL in .env.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config.settings import DATABASE_URL

# SQLite requires check_same_thread=False when used with async frameworks
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,   # detect stale connections
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yield a DB session and close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined in ORM models."""
    # Import models so Base.metadata is populated before create_all
    from backend.models import user_model, alert_model, camera_model  # noqa: F401
    Base.metadata.create_all(bind=engine)
