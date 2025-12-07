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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users", response_model=schemas.UserResponse)
def create_user(request: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_email = db.query(models.User).filter_by(email=request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(models.User).filter_by(username=request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
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
        password_hash=hashed
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", response_model=schemas.Token)
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
    
    token = auth.create_access_token(sub=user.email)
    return {"access_token": token, "token_type": "bearer"}


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
            or_(*[func.json_contains(models.UserStory.assignees, f'"{a}"') for a in assignee_list])
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
        
        # Calculate MVP score: Business Value (default 5) / Story Points
        # Business value is always 5 by default
        business_value = 5
        if s.story_points is not None and s.story_points != 0 and s.story_points > 0:
            s.mvp_score = business_value / s.story_points
        else:
            s.mvp_score = 0.0

    # Sort stories by MVP score (descending), then by MoSCoW priority if available
    # MoSCoW priority order: Must > Should > Could > Won't
    moscow_order = {"Must": 4, "Should": 3, "Could": 2, "Won't": 1}
    
    def sort_key(story):
        moscow_priority_score = moscow_order.get(story.moscow_priority, 0)
        return (-story.mvp_score, -moscow_priority_score)
    
    stories = sorted(stories, key=sort_key, reverse=True)

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
        moscow_priority=request.moscow_priority,
        activity=initial_activity,
        created_by=current_user.username
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

    # Track story points changes - Always use request value (even if None) to allow clearing
    story_points_value = request.story_points
    if story.story_points != story_points_value:
        old_points = story.story_points if story.story_points is not None else "None"
        new_points = story_points_value if story_points_value is not None else "None"
        activity_entry = f"[{timestamp}] {username}: Changed story points from {old_points} to {new_points}"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
    # Always set the value from request (even if None) to allow clearing
    story.story_points = story_points_value

    # Track acceptance criteria changes - use request value if provided (even if empty list)
    acceptance_criteria_value = request.acceptance_criteria if request.acceptance_criteria is not None else story.acceptance_criteria
    if story.acceptance_criteria != acceptance_criteria_value:
        activity_entry = f"[{timestamp}] {username}: Updated acceptance criteria"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.acceptance_criteria = acceptance_criteria_value
    else:
        # Ensure it's set even if not changing
        story.acceptance_criteria = acceptance_criteria_value

    # Track MoSCoW priority changes - Always use request value (even if None) to allow clearing
    moscow_priority_to_set = request.moscow_priority
    if story.moscow_priority != moscow_priority_to_set:
        old_priority = story.moscow_priority if story.moscow_priority is not None else "None"
        new_priority = moscow_priority_to_set if moscow_priority_to_set is not None else "None"
        activity_entry = f"[{timestamp}] {username}: Changed MoSCoW priority from '{old_priority}' to '{new_priority}'"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
    # Always set the value from request (even if None) to allow clearing
    story.moscow_priority = moscow_priority_to_set
    # Mark moscow_priority as modified to ensure SQLAlchemy detects the change (especially for None)
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(story, "moscow_priority")

    # If activity is provided in request (new comments), add them
    if request.activity:
        # Create a new list from existing activity to ensure SQLAlchemy detects the change
        updated_activity = list(story.activity) if story.activity else []
        for activity_item in request.activity:
            # Check if it's a manual comment (has "text" property)
            if isinstance(activity_item, dict) and "text" in activity_item:
                new_entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "user": username,
                    "action": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {username}: Comment: {activity_item['text']}"
                }
                updated_activity.append(new_entry)
        # Only update if new comments were added
        if len(updated_activity) > (len(story.activity) if story.activity else 0):
            story.activity = updated_activity
            # Mark activity as modified to ensure SQLAlchemy saves it
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(story, "activity")

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
        models.UserStory.assignee == username
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
