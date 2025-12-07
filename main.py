import auth
from auth import create_access_token, verify_access_token
from schemas import UserCreate, UserResponse
from passlib.context import CryptContext
import schemas
import models
from datetime import date, datetime
from typing import Optional
from database import SessionLocal
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi import FastAPI, Depends, HTTPException, status
from dotenv import load_dotenv
from sqlalchemy import func
from fastapi import Query
from sqlalchemy import or_
from sqlalchemy import and_
load_dotenv()

app = FastAPI(title="Requirements Engineering Tool Prototype")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_STATUSES = [
    "Backlog",
    "Proposed",
    "Needs Refinement",
    "In Refinement",
    "Ready To Commit",
    "Sprint Ready",
]

STATUS_CANONICAL = {s.lower(): s for s in VALID_STATUSES}

STATUS_TRANSITIONS = {
    "Backlog": {"Proposed"},
    "Proposed": {"Needs Refinement", "Backlog"},
    "Needs Refinement": {"In Refinement", "Proposed"},
    "In Refinement": {"Ready To Commit", "Needs Refinement"},
    "Ready To Commit": {"Sprint Ready", "In Refinement"},
    "Sprint Ready": {"Ready To Commit"},
}


def ensure_valid_status_or_400(raw_status: Optional[str]) -> str:
    """
    Make sure status is one of VALID_STATUSES.
    Returns canonical label (e.g. 'Backlog') or raises HTTP 400.
    """
    if raw_status is None or raw_status == "":
        # default if missing
        return "Backlog"

    key = raw_status.strip().lower()
    canonical = STATUS_CANONICAL.get(key)
    if not canonical:
        allowed = ", ".join(VALID_STATUSES)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{raw_status}'. Allowed values: {allowed}",
        )
    return canonical


def validate_status_transition_or_400(old_status: str, new_status: str):
    """
    Enforce allowed movements between statuses using STATUS_TRANSITIONS.
    Both old_status and new_status can be any case; they are canonicalized first.
    """
    if old_status is None or new_status is None:
        return

    old_canon = ensure_valid_status_or_400(old_status)
    new_canon = ensure_valid_status_or_400(new_status)

    # No movement? Always allowed.
    if old_canon == new_canon:
        return

    allowed_targets = STATUS_TRANSITIONS.get(old_canon, set())
    if new_canon not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{old_canon}' to '{new_canon}'.",
        )


def enforce_transition_criteria_or_400(
    old_status: str,
    new_status: str,
    request: schemas.StoryCreate,
    story: models.UserStory,
):
    """
    Enforce extra business rules for specific status transitions.

    Backlog -> Proposed:
        - description present
        - bv present

    Proposed -> Needs Refinement:
        - description present
        - bv present
        - acceptance_criteria non-empty

    Needs Refinement -> In Refinement:
        - refinement_session_scheduled = True
        - groomed = True
        - dependencies non-empty
        - session_documented = True

    In Refinement -> Ready To Commit:
        - story_points present
        - acceptance_criteria non-empty
        - refinement_dependencies non-empty
        - team_approval = True
        - po_approval = True

    Ready To Commit -> Sprint Ready:
        - sprint_capacity present
        - skills_available = True
        - team_commits = True
        - tasks_identified = True
    """

    # Helper: prefer request value if explicitly provided, else fall back to DB
    def effective(name: str):
        req_val = getattr(request, name, None)
        return req_val if req_val is not None else getattr(story, name, None)

    # ----- Backlog -> Proposed -----
    if old_status == "Backlog" and new_status == "Proposed":
        desc = request.description if request.description is not None else story.description
        if not desc or not desc.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move Backlog → Proposed without a basic description.",
            )

        bv = effective("bv")
        if bv is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move Backlog → Proposed without BV (business value).",
            )

    # ----- Proposed -> Needs Refinement -----
    if old_status == "Proposed" and new_status == "Needs Refinement":
        missing = []

        desc = request.description if request.description is not None else story.description
        if not desc or not desc.strip():
            missing.append("Basic Description")

        bv = effective("bv")
        if bv is None:
            missing.append("BV")

        ac = (
            request.acceptance_criteria
            if request.acceptance_criteria is not None
            else story.acceptance_criteria
        )
        if not ac:
            missing.append("Acceptance Criteria")

        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Cannot move Proposed → Needs Refinement. Missing: " +
                    ", ".join(missing)
                ),
            )

    # ----- Needs Refinement -> In Refinement -----
    if old_status == "Needs Refinement" and new_status == "In Refinement":
        missing = []

        rss = effective("refinement_session_scheduled")
        if not rss:
            missing.append("Refinement Session Scheduled")

        groomed = effective("groomed")
        if not groomed:
            missing.append("Groomed")

        deps = effective("dependencies")
        if not deps or len(deps) == 0:
            missing.append("Dependencies")

        session_doc = effective("session_documented")
        if not session_doc:
            missing.append("Session Documented")

        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Cannot move Needs Refinement → In Refinement. Missing: "
                    + ", ".join(missing)
                ),
            )

    # ----- In Refinement -> Ready To Commit -----
    if old_status == "In Refinement" and new_status == "Ready To Commit":
        missing = []

        # Story Estimates: story_points
        sp = (
            request.story_points
            if request.story_points is not None
            else story.story_points
        )
        if sp is None:
            missing.append("Story Estimates")

        # Acceptance Criteria
        ac = (
            request.acceptance_criteria
            if request.acceptance_criteria is not None
            else story.acceptance_criteria
        )
        if not ac:
            missing.append("Acceptance Criteria")

        # In Refinement Dependencies
        ref_deps = effective("refinement_dependencies")
        if not ref_deps or len(ref_deps) == 0:
            missing.append("In Refinement Dependencies")

        team_approval = effective("team_approval")
        if not team_approval:
            missing.append("Team Approval")

        po_approval = effective("po_approval")
        if not po_approval:
            missing.append("PO Approval")

        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Cannot move In Refinement → Ready To Commit. Missing: "
                    + ", ".join(missing)
                ),
            )

    # ----- Ready To Commit -> Sprint Ready -----
    if old_status == "Ready To Commit" and new_status == "Sprint Ready":
        missing = []

        sprint_capacity = effective("sprint_capacity")
        if sprint_capacity is None:
            missing.append("Sprint Capacity")

        skills_available = effective("skills_available")
        if not skills_available:
            missing.append("Skills Available")

        team_commits = effective("team_commits")
        if not team_commits:
            missing.append("Team Commits")

        tasks_identified = effective("tasks_identified")
        if not tasks_identified:
            missing.append("Tasks Identified")

        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Cannot move Ready To Commit → Sprint Ready. Missing: "
                    + ", ".join(missing)
                ),
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
):
    creds = verify_access_token(token)
    email = creds.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@app.post("/users", response_model=schemas.UserResponse)
def create_user(request: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_email = db.query(models.User).filter_by(
        email=request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    existing_username = db.query(models.User).filter_by(
        username=request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Validate role_code if provided
    if request.role_code:
        role = db.query(models.Role).filter_by(code=request.role_code).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role code: {request.role_code}"
            )

    name_parts = request.name.strip().split(maxsplit=1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    hashed = pwd_context.hash(request.password)
    user = models.User(
        username=request.username,
        first_name=first_name,
        last_name=last_name,
        email=request.email,
        password_hash=hashed,
        role_code=request.role_code
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", response_model=schemas.LoginResponse)
def login_json(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(email=request.email).first()

    # Check if user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )

    # Check if password is correct
    if not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    # Check if user has a role assigned
    if not user.role_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contact Product Manager to assign role"
        )

    token = auth.create_access_token(sub=user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@app.post("/logout")
def logout():
    """
    Dummy logout endpoint – client should discard its JWT.
    """
    return {"message": "Successfully logged out"}


@app.post("/forgot-password")
def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Verify if email exists for password reset.
    Returns success if email exists, 404 if not found.
    """
    user = db.query(models.User).filter_by(email=request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )

    return {"message": "Email verified", "email": request.email}


@app.post("/reset-password")
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset user's password.
    """
    user = db.query(models.User).filter_by(email=request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email"
        )

    # Hash the new password and update
    user.password_hash = pwd_context.hash(request.new_password)
    db.commit()

    return {"message": "Password reset successfully"}


@app.get("/roles", response_model=list[schemas.RoleResponse])
def get_all_roles(db: Session = Depends(get_db)):
    """
    Get all available roles.
    """
    roles = db.query(models.Role).all()
    return roles


@app.get("/users", response_model=list[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    """
    Get all users with their roles.
    """
    users = db.query(models.User).all()
    return users


@app.patch("/users/{user_id}/role", response_model=schemas.UserResponse)
def update_user_role(
    user_id: int,
    request: schemas.UpdateRoleRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if current user has permission (must be product-manager)
    if current_user.role_code != "product-manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Don't have permission to perform this action"
        )

    user = db.query(models.User).filter_by(id=user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate if role exists
    role = db.query(models.Role).filter_by(code=request.role_code).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role code: {request.role_code}. Valid roles are: product-manager, stakeholder, dev-team, scrum-master"
        )

    user.role_code = request.role_code
    db.commit()
    db.refresh(user)

    return user


def parse_multi(value):
    if not value:
        return None
    if isinstance(value, list):
        raw = value
    else:
        raw = value.split(",")
    return [v.strip().lower() for v in raw if v.strip()]


@app.get("/stories", response_model=list[schemas.StoryResponse])
def get_stories(
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
    created_by: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.UserStory)
    assignee_list = parse_multi(assignee)
    status_list = parse_multi(status)
    tags_list = parse_multi(tags)
    created_list = parse_multi(created_by)

    if assignee_list:
        # Filter by assignees JSON array - check if any requested assignee is in the array
        query = query.filter(
            or_(*[func.json_contains(models.UserStory.assignees,
                f'"{a}"') for a in assignee_list])
        )

    if status_list:
        query = query.filter(
            or_(*[func.lower(models.UserStory.status) == s for s in status_list])
        )

    if created_list:
        query = query.filter(
            or_(*[func.lower(models.UserStory.created_by) == c for c in created_list])
        )

    if tags_list:
        query = query.filter(models.UserStory.tags.isnot(None))
        query = query.filter(models.UserStory.tags != "")
        query = query.filter(
            or_(*[
                func.lower(models.UserStory.tags).like(f"%{t}%")
                for t in tags_list
            ])
        )

    if start_date:
        query = query.filter(models.UserStory.created_on >= start_date)

    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(models.UserStory.created_on <= end_dt)

    stories = query.all()

    for s in stories:
        if isinstance(s.tags, str):
            s.tags = [tag.strip() for tag in s.tags.split(",") if tag.strip()]

    return stories


@app.post("/stories")
def add_story(request: schemas.StoryCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not request.title or not request.title.strip():
        raise HTTPException(
            status_code=400, detail={"message": "Title cannot be empty"}
        )
    if not request.description or not request.description.strip():
        raise HTTPException(
            status_code=400, detail={"message": "Description cannot be empty"}
        )
    request.status = ensure_valid_status_or_400(request.status)
    # Assignees is optional - default to empty list
    assignees_value = request.assignees if request.assignees else []

    tags_value = None
    if isinstance(request.tags, list):
        tags_value = ",".join(request.tags)
    elif isinstance(request.tags, str):
        tags_value = request.tags
    else:
        tags_value = ""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    initial_activity = [
        {
            "timestamp": timestamp,
            "user": current_user.username,
            "action": f"[{timestamp}] {current_user.username}: Created story"
        }
    ]

    new_story = models.UserStory(
        title=request.title,
        description=request.description,
        assignees=assignees_value,
        status=request.status,
        tags=tags_value,
        acceptance_criteria=request.acceptance_criteria or [],
        story_points=request.story_points,
        activity=initial_activity,
        created_by=current_user.username,
        bv=getattr(request, "bv", None),
        refinement_session_scheduled=getattr(
            request, "refinement_session_scheduled", None),
        groomed=getattr(request, "groomed", None),
        dependencies=getattr(request, "dependencies", None),
        session_documented=getattr(request, "session_documented", None),
        refinement_dependencies=getattr(
            request, "refinement_dependencies", None),
        team_approval=getattr(request, "team_approval", None),
        po_approval=getattr(request, "po_approval", None),
        sprint_capacity=getattr(request, "sprint_capacity", None),
        skills_available=getattr(request, "skills_available", None),
        team_commits=getattr(request, "team_commits", None),
        tasks_identified=getattr(request, "tasks_identified", None)
    )
    db.add(new_story)
    db.commit()
    db.refresh(new_story)

    # Convert to StoryResponse schema to ensure proper camelCase serialization
    story_response = schemas.StoryResponse.from_orm(new_story)
    return {"message": "Story added successfully", "story": story_response}


@app.put("/stories/{story_id}")
def update_story(story_id: int, request: schemas.StoryCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    story = db.query(models.UserStory).filter(
        models.UserStory.id == story_id).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )

    if not story.activity:
        story.activity = []

    old_status = story.status
    desired_status = request.status if request.status is not None else old_status
    canonical_old = ensure_valid_status_or_400(old_status)
    canonical_new = ensure_valid_status_or_400(desired_status)
    validate_status_transition_or_400(canonical_old, canonical_new)
    enforce_transition_criteria_or_400(
        canonical_old, canonical_new, request, story)
    request.status = canonical_new

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = current_user.username

    # Track title changes
    if story.title != request.title:
        activity_entry = f"[{timestamp}] {username}: Changed title from '{story.title}' to '{request.title}'"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.title = request.title

    # Track description changes
    if story.description != request.description:
        activity_entry = f"[{timestamp}] {username}: Updated description"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.description = request.description

    # Track assignees changes
    old_assignees = story.assignees or []
    new_assignees = request.assignees or []
    if set(old_assignees) != set(new_assignees):
        old_str = ", ".join(old_assignees) if old_assignees else "None"
        new_str = ", ".join(new_assignees) if new_assignees else "None"
        activity_entry = f"[{timestamp}] {username}: Changed assignees from '{old_str}' to '{new_str}'"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.assignees = new_assignees

    # Track status changes
    if story.status != request.status:
        activity_entry = f"[{timestamp}] {username}: Changed status from '{story.status}' to '{request.status}'"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.status = request.status

    # Handle tags
    tags_value = None
    if isinstance(request.tags, list):
        tags_value = ",".join(request.tags)
    elif isinstance(request.tags, str):
        tags_value = request.tags

    if story.tags != tags_value:
        activity_entry = f"[{timestamp}] {username}: Updated tags"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.tags = tags_value

    # Track story points changes - PRESERVE if not provided in request
    story_points_value = request.story_points if request.story_points is not None else story.story_points
    if story.story_points != story_points_value:
        old_points = story.story_points or "None"
        new_points = story_points_value or "None"
        activity_entry = f"[{timestamp}] {username}: Changed story points from {old_points} to {new_points}"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.story_points = story_points_value
    else:
        # Ensure it's set even if not changing
        story.story_points = story_points_value

    # Track acceptance criteria changes - use request value if provided (even if empty list)
        # Track acceptance criteria changes - use request value if provided (even if empty list)
    acceptance_criteria_value = (
        request.acceptance_criteria
        if request.acceptance_criteria is not None
        else story.acceptance_criteria
    )
    if story.acceptance_criteria != acceptance_criteria_value:
        activity_entry = f"[{timestamp}] {username}: Updated acceptance criteria"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry}
        )
        story.acceptance_criteria = acceptance_criteria_value
    else:
        # Ensure it's set even if not changing
        story.acceptance_criteria = acceptance_criteria_value

    # If activity is provided in request (new comments), add them
    if request.activity:
        # Create a new list from existing activity to ensure SQLAlchemy detects the change
        updated_activity = list(story.activity) if story.activity else []
        for activity_item in request.activity:
            # Check if it's a manual comment (has "text" property)
            if isinstance(activity_item, dict) and "text" in activity_item:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_entry = {
                    "timestamp": now_str,
                    "user": username,
                    "action": f"[{now_str}] {username}: Comment: {activity_item['text']}",
                }
                updated_activity.append(new_entry)

        # Only update if new comments were actually added
        if len(updated_activity) > (len(story.activity) if story.activity else 0):
            story.activity = updated_activity
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(story, "activity")

    # Keep criteria fields in sync (if columns exist)
    if hasattr(story, "bv"):
        story.bv = getattr(request, "bv", story.bv)
    if hasattr(story, "refinement_session_scheduled"):
        story.refinement_session_scheduled = getattr(
            request,
            "refinement_session_scheduled",
            story.refinement_session_scheduled,
        )
    if hasattr(story, "groomed"):
        story.groomed = getattr(request, "groomed", story.groomed)
    if hasattr(story, "dependencies"):
        story.dependencies = getattr(
            request, "dependencies", story.dependencies)
    if hasattr(story, "session_documented"):
        story.session_documented = getattr(
            request, "session_documented", story.session_documented
        )
    if hasattr(story, "refinement_dependencies"):
        story.refinement_dependencies = getattr(
            request, "refinement_dependencies", story.refinement_dependencies
        )
    if hasattr(story, "team_approval"):
        story.team_approval = getattr(
            request, "team_approval", story.team_approval)
    if hasattr(story, "po_approval"):
        story.po_approval = getattr(request, "po_approval", story.po_approval)
    if hasattr(story, "sprint_capacity"):
        story.sprint_capacity = getattr(
            request, "sprint_capacity", story.sprint_capacity
        )
    if hasattr(story, "skills_available"):
        story.skills_available = getattr(
            request, "skills_available", story.skills_available
        )
    if hasattr(story, "team_commits"):
        story.team_commits = getattr(
            request, "team_commits", story.team_commits)
    if hasattr(story, "tasks_identified"):
        story.tasks_identified = getattr(
            request, "tasks_identified", story.tasks_identified
        )

    db.commit()
    db.refresh(story)

    # Convert to StoryResponse schema to ensure proper camelCase serialization
    story_response = schemas.StoryResponse.from_orm(story)
    return {"message": "Story updated successfully", "story": story_response}


@app.delete("/stories/{story_id}")
def delete_story(story_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    story = db.query(models.UserStory).filter(
        models.UserStory.id == story_id).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )

    db.delete(story)
    db.commit()
    return {"message": "Story deleted successfully", "id": story_id}

# Endpoint for filtering ideas


@app.get("/filter", response_model=list[schemas.StoryResponse])
def filter_stories(search: Optional[str] = None, db: Session = Depends(get_db)):
    if not search:
        return db.query(models.UserStory).all()

    if search.isdigit():
        story_id = int(search)
        return db.query(models.UserStory).filter(models.UserStory.id == story_id).all()
    else:
        return db.query(models.UserStory).filter(models.UserStory.title.icontains(search)).all()


@app.get("/profile", response_model=schemas.UserResponse)
def get_user_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/workspace", response_model=schemas.WorkspaceSummary)
def get_workspace_data(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    username = current_user.username

    stories = db.query(models.UserStory).filter(
        models.UserStory.assignees == username
    ).all()

    by_status = {}
    for s in stories:
        by_status[s.status] = by_status.get(s.status, 0) + 1
    return schemas.WorkspaceSummary(
        username=username,
        total_stories=len(stories),
        by_status=by_status,
        stories=stories,
    )


@app.get("/backlog", response_model=list[schemas.StoryResponse])
def get_backlog_stories(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    stories = db.query(models.UserStory).filter(
        models.UserStory.status == "Backlog"
    ).all()

    for s in stories:
        if isinstance(s.tags, str):
            s.tags = [tag.strip() for tag in s.tags.split(",") if tag.strip()]
    return stories
