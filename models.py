
from __future__ import annotations

import os
from dotenv import load_dotenv

from typing import List, Optional

from sqlalchemy import create_engine, Column, String, BigInteger, DateTime, ForeignKey, func, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from datetime import datetime

load_dotenv()  # Take environment variables from .env.

database_url = os.getenv('DATABASE_URL')

# --- DATABASE CONNECTION SETUP ---
DATABASE_URL = database_url
engine = create_engine(DATABASE_URL)


# Define the base class for models
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    # --- 1. ESSENTIAL COLUMNS (The Core) ---
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Permission & Access Control
    role: Mapped[str] = mapped_column(String(50), server_default="employee")
    status: Mapped[str] = mapped_column(String(20), server_default="pending_approval")

    # Automatic timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # --- 2. OFFICE AUTOMATION COLUMNS (The Work Layer) ---
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    job_title: Mapped[Optional[str]] = mapped_column(String(100))
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))

    # Self-Referencing Foreign Key for manager hierarchy
    manager_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    manager = relationship("User", remote_side=[user_id], backref="subordinates")

    last_seen: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self):
        return f"User(id={self.user_id!r}, name={self.full_name or self.first_name!r}, role={self.role!r})"


class Issue(Base):
    """
    Tracks company issues/problems that are broadcast to users.
    Each issue gets a unique ID for reference and can be closed by admins.
    """
    __tablename__ = 'issues'

    # Auto-incrementing ID for issues (like ISSUE-001, ISSUE-002, etc.)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # The actual message content describing the issue
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)

    # Who created this issue (admin user_id)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))

    # Status: 'open' or 'closed'
    status: Mapped[str] = mapped_column(String(20), server_default="open")

    # When the issue was broadcast
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Resolution details (when closed)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Telegram message ID for tracking (optional, for editing/deleting)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_issues")
    closer = relationship("User", foreign_keys=[closed_by], backref="closed_issues")

    def __repr__(self):
        return f"Issue(id={self.id!r}, status={self.status!r}, created_by={self.created_by!r})"

    def get_issue_id(self):
        """Returns formatted issue ID like ISSUE-001"""
        return f"ISSUE-{self.id:03d}"


def init_db():
    """Creates all tables in the database."""
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully.")


if __name__ == "__main__":
    init_db()
