from typing import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Database configuration
DB_URI = 'sqlite:///scheduler.db'
# Create the engine and session
engine = create_engine(DB_URI)
session = Session(engine)
