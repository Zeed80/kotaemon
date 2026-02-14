from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from ktem.db.engine import engine


# TODO: simplify with using SQLAlchemy directly
class Index(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "ktem__index"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    index_type: str = Field()
    config: dict = Field(default={}, sa_column=Column(JSON))


Index.metadata.create_all(engine)
