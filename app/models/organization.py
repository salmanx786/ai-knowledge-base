from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ORMBase


class Organization(ORMBase):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
