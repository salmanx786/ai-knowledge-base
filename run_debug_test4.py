from sqlalchemy import BigInteger, Integer, Column, Identity
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger().with_variant(Integer, "sqlite"), Identity(always=False), primary_key=True)
    name = Column(Integer)

engine = create_engine('sqlite:///:memory:', echo=True)
Base.metadata.create_all(engine)
with engine.begin() as conn:
    conn.execute(User.__table__.insert().values(name=1))
