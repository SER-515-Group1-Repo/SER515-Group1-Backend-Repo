from sqlalchemy import Column, Integer, String, Text, DateTime, func, Boolean
from database import Base


class UserStory(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    description = Column(Text, nullable=False)
    assignee = Column(String(250), nullable=False, server_default="Unassigned")
    status = Column(String(250), nullable=False, server_default="In Progress")
    tags = Column(String(500), nullable=True)
    created_by = Column(String(250), nullable=True)
    created_on = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(250), nullable=False, unique=True, index=True)
    first_name = Column(String(250), nullable=False)
    last_name = Column(String(250), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="1")
    created_on = Column(DateTime(timezone=True), server_default=func.now())