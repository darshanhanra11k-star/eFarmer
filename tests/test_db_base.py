from typing import cast

from sqlalchemy import Integer, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.base import Base


def test_base_is_declarative_base() -> None:
    assert issubclass(Base, DeclarativeBase)


def test_model_registers_in_metadata() -> None:
    class _TestMetadataModel(Base):
        __tablename__ = "_test_metadata_model"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)

    try:
        assert "_test_metadata_model" in Base.metadata.tables
    finally:
        Base.metadata.remove(cast(Table, _TestMetadataModel.__table__))
