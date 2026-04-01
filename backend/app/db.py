import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class CarrierRecord(Base):
    __tablename__ = "carriers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class QuoteRecord(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parsed_data_json: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


def _normalize_sqlite_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///./"):
        relative_path = database_url.removeprefix("sqlite:///./")
        db_path = Path(__file__).resolve().parent.parent / relative_path
        return f"sqlite:///{db_path}"
    return database_url


DATABASE_URL = _normalize_sqlite_url(settings.DATABASE_URL)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


DEFAULT_CARRIERS = [
    {"name": "Carrier A", "email": "quotes@carriera.com", "phone": "123-456-7890"},
    {"name": "Carrier B", "email": "rates@carrierb.com", "phone": "234-567-8901"},
    {"name": "Carrier C", "email": "dispatch@carrierc.com", "phone": "345-678-9012"},
]


def init_database() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        existing_carrier = session.scalar(select(CarrierRecord.id).limit(1))
        if existing_carrier is None:
            session.add_all(CarrierRecord(**carrier) for carrier in DEFAULT_CARRIERS)
            session.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_parsed_data(parsed_data: dict) -> str:
    return json.dumps(parsed_data)
