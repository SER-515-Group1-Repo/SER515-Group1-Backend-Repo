from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

from helper import to_camel_case


class StoryCreate(BaseModel):
    title: str = Field(..., description="Title of the story")
    description: str = Field(..., description="Description of the story")
    assignee: Optional[str] = Field(
        default="Unassigned", description="Person assigned to the story")
    status: Optional[str] = Field(
        default="In Progress", description="Current status of the story")
    tags: Optional[str] = Field(default=None, description="Comma-separated tags")


class StoryResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignee: Optional[str]
    status: str
    tags: Optional[str]
    created_by: Optional[str]
    created_on: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )

class UserCreate(BaseModel):
    name: str = Field(..., description="Full name (will split into first/last)")
    username: str = Field(..., description="Unique username for story assignment")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="Plain-text password")

class UserResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    is_active: bool
    created_on: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )

class LoginRequest(BaseModel):
    email: EmailStr  # login uses email
    password: str
class Token(BaseModel):
    access_token: str
    token_type: str  # always "bearer"

class WorkspaceSummary(BaseModel):
    username: str
    total_stories: int
    by_status: dict
    stories: list[StoryResponse]
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )