from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional, List

from flask_login import UserMixin
from sqlalchemy import Enum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import db, login_manager, bcrypt


class Department(enum.Enum):
    GIFTS = "GIFTS"
    STATIONERY = "STATIONERY"
    TOYS = "TOYS"
    BOOKS = "BOOKS"


class RequirementStatus(enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    FULFILLED = "FULFILLED"


@login_manager.user_loader
def load_user(user_id: str) -> Optional["User"]:
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]
    department: Mapped[Department] = mapped_column(Enum(Department), index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_requirements: Mapped[List["Requirement"]] = relationship(
        back_populates="created_by",
        foreign_keys="Requirement.created_by_id",
    )
    assigned_requirements: Mapped[List["Requirement"]] = relationship(
        back_populates="assigned_to",
        foreign_keys="Requirement.assigned_to_id",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)


class Requirement(db.Model):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(index=True)
    contact_info: Mapped[str]
    details: Mapped[str]
    image_filename: Mapped[Optional[str]] = mapped_column(nullable=True)
    staff_name: Mapped[str] = mapped_column(index=True, default="Unassigned")
    status: Mapped[RequirementStatus] = mapped_column(
        Enum(RequirementStatus), default=RequirementStatus.NEW, index=True
    )
    department: Mapped[Department] = mapped_column(Enum(Department), index=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_by: Mapped[User] = relationship(
        "User", back_populates="created_requirements", foreign_keys=[created_by_id]
    )

    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    assigned_to: Mapped[Optional[User]] = relationship(
        "User", back_populates="assigned_requirements", foreign_keys=[assigned_to_id]
    )


