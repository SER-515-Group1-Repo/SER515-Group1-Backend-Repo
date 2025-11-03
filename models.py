from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class UserStory(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    description = Column(Text, nullable=False)
    assignee = Column(String(250), nullable=False, server_default="Unassigned")
    status = Column(String(250), nullable=False, server_default="In Progress")
    created_on = Column(DateTime(timezone=True), server_default=func.now())
