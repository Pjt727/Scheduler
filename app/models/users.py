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
import hashlib
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

    @staticmethod
    def hash_password(password: str) -> str:
        hash_object = hashlib.sha256()
        hash_object.update(password.encode("utf-8"))
        return hash_object.hexdigest()

    @staticmethod
    def password_is_complex(password: str) -> tuple[str, bool]:
        # maybe add some other password checks
        PASS_LEN = 8
        if len(password) < PASS_LEN:
            return f"Password length must be at least {PASS_LEN}", False
        return "", True
