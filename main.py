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
    "http://localhost:3000",
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
    if not user or not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    token = auth.create_access_token(sub=user.email)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/logout")
def logout():
    """
    Dummy logout endpoint – client should discard its JWT.
    """
    return {"message": "Successfully logged out"}


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
        query = query.filter(
            or_(*[func.lower(models.UserStory.assignee) == a for a in assignee_list])
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

    stories = query.order_by(models.UserStory.position.asc()).all()

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
    if not request.assignee or not request.assignee.strip():
        raise HTTPException(
            status_code=400, detail={"message": "Assignee cannot be empty"}
        )
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
    max_position = db.query(func.max(models.UserStory.position)).scalar()
    next_position = (max_position or 0) + 1 if max_position is not None else 0

    new_story = models.UserStory(
        title=request.title,
        description=request.description,
        assignee=request.assignee,
        status=request.status,
        tags=tags_value,
        acceptance_criteria=request.acceptance_criteria or [],
        story_points=request.story_points,
        activity=initial_activity,
        created_by=current_user.username,
        position=next_position
    )
    db.add(new_story)
    db.commit()
    db.refresh(new_story)

    # Convert to StoryResponse schema to ensure proper camelCase serialization
    story_response = schemas.StoryResponse.from_orm(new_story)
    return {"message": "Story added successfully", "story": story_response}

@app.put("/stories/reorder")
def reorder_stories(
    request: schemas.StoryReorderRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Update each story in the new order
        for item in request.reordered_stories:
            story = db.query(models.UserStory).filter(
                models.UserStory.id == item.story_id
            ).first()

            if not story:
                raise HTTPException(
                    status_code=404,
                    detail=f"Story {item.story_id} not found"
                )

            story.position = item.new_position

        db.commit()
        return {"message": "Reordering successful"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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

    # Track assignee changes
    if story.assignee != request.assignee:
        activity_entry = f"[{timestamp}] {username}: Changed assignee from '{story.assignee}' to '{request.assignee}'"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.assignee = request.assignee

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

    # Track acceptance criteria changes - PRESERVE if not provided in request
    acceptance_criteria_value = request.acceptance_criteria if request.acceptance_criteria else story.acceptance_criteria
    if story.acceptance_criteria != acceptance_criteria_value:
        activity_entry = f"[{timestamp}] {username}: Updated acceptance criteria"
        story.activity.append(
            {"timestamp": timestamp, "user": username, "action": activity_entry})
        story.acceptance_criteria = acceptance_criteria_value
    else:
        # Ensure it's set even if not changing
        story.acceptance_criteria = acceptance_criteria_value

    # If activity is provided in request (new comments), add them
    if request.activity and len(request.activity) > len(story.activity):
        # Only add new activities that weren't already tracked
        for activity_item in request.activity:
            if activity_item not in story.activity:
                # Check if it's a manual comment (doesn't start with timestamp pattern)
                if isinstance(activity_item, dict) and "text" in activity_item:
                    new_entry = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "user": username,
                        "action": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {username}: {activity_item['text']}"
                    }
                    story.activity.append(new_entry)

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
