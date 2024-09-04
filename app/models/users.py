from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Enum,
    ForeignKeyConstraint,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.sql.expression import case
from sqlalchemy.orm import Mapped, validates
from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy.util import hybridmethod, hybridproperty
from models.config import session, Base
from models.core import Professor
import enum
from datetime import time, datetime
from typing import Optional, List


class User(Base):
    __tablename__ = "Users"
    email: Mapped[str] = mapped_column(String(), primary_key=True)
    password: Mapped[str] = mapped_column(String())
    professor_id: Mapped[Professor] = mapped_column(Integer(), ForeignKey("Professors.id"))

    professor: Mapped["Professor"] = relationship(Professor, back_populates="user", uselist=False)
