from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Optional, List, Union
from datetime import datetime

from helper import to_camel_case

# Fibonacci sequence values for story points (Agile/Scrum industry standard)
# Values beyond 13 indicate story should be broken down into smaller tasks
VALID_STORY_POINTS = [0, 1, 2, 3, 5, 8, 13, 21]


class StoryCreate(BaseModel):
    title: str = Field(..., description="Title of the story")
    description: str = Field(..., description="Description of the story")
    assignees: Optional[List[str]] = Field(
        default=[], description="List of people assigned to the story")
    status: Optional[str] = Field(
        default="Backlog", description="Current status of the story")
    tags: Optional[Union[List[str], str]] = None
    acceptance_criteria: Optional[list] = Field(
        default=[], description="List of acceptance criteria (max 5)")
    story_points: Optional[int] = Field(
        default=None, description="Story points (Fibonacci: 0,1,2,3,5,8,13,21,34,55,89)")
    activity: Optional[list] = Field(
        default=[], description="Activity/comments log")
    bv: Optional[int] = Field(
        default=None,
        description="Business value (required when moving Backlog → Proposed)",
    )
    refinement_session_scheduled: Optional[bool] = Field(
        default=False,
        description="Checklist: refinement session scheduled (Proposed → Needs Refinement)",
    )
    groomed: Optional[bool] = Field(
        default=False,
        description="Checklist: story is groomed (Proposed → Needs Refinement)",
    )
    dependencies: Optional[list] = Field(
        default=[],
        description="Dependencies for the story, like AC (Proposed → Needs Refinement)",
    )
    session_documented: Optional[bool] = Field(
        default=False,
        description="Checklist: refinement session documented (Proposed → Needs Refinement)",
    )
    refinement_dependencies: Optional[list] = Field(
        default=[],
        description="Dependencies identified during In Refinement stage",
    )
    team_approval: Optional[bool] = Field(
        default=False,
        description="Team approval for moving In Refinement → Ready To Commit",
    )
    po_approval: Optional[bool] = Field(
        default=False,
        description="PO approval for moving In Refinement → Ready To Commit",
    )

    # ----- Ready To Commit → Sprint Ready criteria -----
    sprint_capacity: Optional[int] = Field(
        default=None,
        description="Sprint capacity used when moving Ready To Commit → Sprint Ready",
    )
    skills_available: Optional[bool] = Field(
        default=False,
        description="Skills available in team for this story",
    )
    team_commits: Optional[bool] = Field(
        default=False,
        description="Team commits to deliver this story in the sprint",
    )
    tasks_identified: Optional[bool] = Field(
        default=False,
        description="Tasks identified for implementation",
    )

    moscow_priority: Optional[str] = Field(default=None, description="MoSCoW priority: Must, Should, Could, Won't")
    activity: Optional[list] = Field(default=[], description="Activity/comments log")
    
    @field_validator("moscow_priority", mode="before")
    @classmethod
    def validate_moscow_priority(cls, v):
        """Validate that MoSCoW priority is one of the valid options"""
        if v is None or v == "" or v == "null":
            return None
        valid_priorities = ["Must", "Should", "Could", "Won't"]
        if v not in valid_priorities:
            raise ValueError(f"MoSCoW priority must be one of: {valid_priorities}")
        return v

    @field_validator("story_points", mode="before")
    @classmethod
    def validate_story_points(cls, v):
        """Validate that story points are in the Fibonacci sequence"""
        if v is None or v == "" or v == "null":
            return None
        # Convert to int if it's a string
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise ValueError(f"Story points must be a number")
        if v not in VALID_STORY_POINTS:
            raise ValueError(
                f"Story points must be a Fibonacci number: {VALID_STORY_POINTS}")
        return v


class StoryResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignees: Optional[List[str]] = None
    status: str
    tags: Optional[List[str]] = None
    acceptance_criteria: Optional[list] = None
    story_points: Optional[int] = None
    moscow_priority: Optional[str] = None
    mvp_score: Optional[float] = None
    activity: Optional[list] = None
    created_by: Optional[str]
    created_on: datetime
    bv: Optional[int] = None
    refinement_session_scheduled: Optional[bool] = None
    groomed: Optional[bool] = None
    dependencies: Optional[list] = None
    session_documented: Optional[bool] = None
    refinement_dependencies: Optional[list] = None
    team_approval: Optional[bool] = None
    po_approval: Optional[bool] = None
    sprint_capacity: Optional[int] = None
    skills_available: Optional[bool] = None
    team_commits: Optional[bool] = None
    tasks_identified: Optional[bool] = None

    @field_validator("assignees", mode="before")
    @classmethod
    def parse_assignees(cls, v):
        """Ensure assignees is always a list"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Handle legacy single assignee as comma-separated or single value
            return [a.strip() for a in v.split(",") if a.strip()]
        return []

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        """Convert string tags to list of strings"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [tag.strip() for tag in v.split(",") if tag.strip()]
        return []

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class UserCreate(BaseModel):
    name: str = Field(...,
                      description="Full name (will split into first/last)")
    username: str = Field(...,
                          description="Unique username for story assignment")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="Plain-text password")
    role_code: Optional[str] = Field(default=None,
                                     description="Role code (product-manager, stakeholder, dev-team, scrum-master)")


class UserResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    is_active: bool
    role_code: Optional[str] = None
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


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address")


class ResetPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    new_password: str = Field(..., min_length=8,
                              description="New password (min 8 characters)")


class UpdateRoleRequest(BaseModel):
    role_code: str = Field(
        ..., description="Role code to assign (product-manager, stakeholder, dev-team, scrum-master)")


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


class RoleResponse(BaseModel):
    code: str
    name: str

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,
        populate_by_name=True,
    )
