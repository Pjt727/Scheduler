from typing import Iterator
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    rowid: Mapped[int]  = mapped_column(Integer, system=True)

# Database configuration
DB_URI = 'sqlite:///scheduler.db'
# Create the engine and session
engine = create_engine(DB_URI)
session = Session(engine)
