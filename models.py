from sqlalchemy import Column, Integer, String, Text, DateTime, func, Boolean, JSON
from database import Base


class UserStory(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    description = Column(Text, nullable=False)
    assignees = Column(JSON, nullable=True, default=[])  # Changed to JSON array for multiple assignees
    status = Column(String(250), nullable=False, server_default="Backlog")
    tags = Column(String(500), nullable=True)
    acceptance_criteria = Column(JSON, nullable=True, default=[])
    story_points = Column(Integer, nullable=True)
    activity = Column(JSON, nullable=True, default=[])
    created_by = Column(String(250), nullable=True)
    created_on = Column(DateTime(timezone=True), server_default=func.now())
    bv = Column(Integer, nullable=True) 
    refinement_session_scheduled = Column(Boolean,nullable=True,)
    groomed = Column(Boolean, nullable=True,)
    dependencies = Column(JSON, nullable=True, default=[])
    session_documented = Column(Boolean, nullable=True)
    refinement_dependencies = Column(JSON, nullable=True, default=[])
    team_approval = Column(Boolean, nullable=True)
    po_approval = Column(Boolean, nullable=True)
    sprint_capacity = Column(Integer, nullable=True)
    skills_available = Column(Boolean, nullable=True)
    team_commits = Column(Boolean, nullable=True)
    tasks_identified = Column(Boolean, nullable=True)

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