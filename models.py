
from __future__ import annotations

import os
from dotenv import load_dotenv

from typing import List, Optional

from sqlalchemy import create_engine, Column, String, BigInteger, DateTime, ForeignKey, func, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


from datetime import datetime
from tabulate import tabulate

load_dotenv()  # Take environment variables from .env.

database_url = os.getenv('DATABASE_URL')

# --- DATABASE CONNECTION SETUP ---
# Replace with your actual Postgres credentials
# format: postgresql://user:password@localhost:port/dbname
DATABASE_URL = database_url
engine = create_engine(DATABASE_URL)

# Define the base class for models
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    # --- 1. ESSENTIAL COLUMNS (The Core) ---
    # We use BigInteger because Baleh IDs are too large for standard Integers
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Permission & Access Control
    # Defaults to 'employee' so new users can't do anything until promoted
    role: Mapped[str] = mapped_column(String(50), server_default="employee")
    # Defaults to 'pending' so you must approve them before they act
    status: Mapped[str] = mapped_column(String(20), server_default="pending_approval")

    # Automatic timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # --- 2. OFFICE AUTOMATION COLUMNS (The Work Layer) ---
    # Internal Company ID (e.g. EMP-001) - Must be unique
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)

    # Real legal name (for official reports)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Routing info: knowing department helps route issues automatically later
    department: Mapped[Optional[str]] = mapped_column(String(100))
    job_title: Mapped[Optional[str]] = mapped_column(String(100))

    # Critical for urgent contact
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))

    # Self-Referencing Foreign Key: "Who is this person's boss?"
    # It points back to the 'user_id' of another row in this same table.
    manager_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.user_id"))

    # SQLAlchemy Relationship (Optional but recommended):
    # Allows you to do: user.subordinates or user.manager in Python code easily
    manager = relationship("User", remote_side=[user_id], backref="subordinates")

    last_seen: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self):
        return f"User(id={self.user_id!r}, name={self.full_name or self.first_name!r}, role={self.role!r})"

async def update_activity(session: AsyncSession, user_id: int):
    """
    Updates the last_seen column.
    We use 'update' specifically for performance instead of loading the whole object.
    """
    try:
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(last_seen=func.now())
        )
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        await session.rollback()
        print(f"Error updating activity for {user_id}: {e}")

def init_db():
    """Creates the tables in the database."""
    Base.metadata.create_all(engine)
    print("✅ Users table created successfully.")