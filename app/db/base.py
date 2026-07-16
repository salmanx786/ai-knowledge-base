from sqlalchemy.orm import DeclarativeBase

from app.db.mixins import IdMixin, TimestampMixin


class Base(DeclarativeBase):
    """Declarative base: owns the SQLAlchemy registry and metadata only.

    Intentionally carries no columns so association/junction tables and
    natural-key tables can inherit it directly without an unwanted ``id``.
    """


class ORMBase(IdMixin, TimestampMixin, Base):
    """Aggregate base for the common case: BIGINT identity PK + timestamps.

    Most tables inherit this. Named ``ORMBase`` (not ``BaseModel``) to avoid
    confusion with Pydantic's ``BaseModel``. Marked ``__abstract__`` so it
    maps no table of its own; the mixins remain usable independently for the
    rare table that needs only some of these columns.
    """

    __abstract__ = True
