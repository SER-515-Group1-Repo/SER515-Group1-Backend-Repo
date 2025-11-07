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


class StoryResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignee: Optional[str]
    status: str
    created_on: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User’s email address")
    password: str = Field(..., min_length=8, description="Plain-text password")

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    created_on: datetime

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )
class Token(BaseModel):
    access_token: str
    token_type: str  # always "bearer"
