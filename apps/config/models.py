from sqlalchemy import Column, Integer, String, ForeignKey
from database.base import Base


class Secrets(Base):
    __tablename__ = 'secrets'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String)
    value = Column(String)
    user = Column(ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
