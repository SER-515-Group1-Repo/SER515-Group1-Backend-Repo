from dotenv import load_dotenv
load_dotenv()   # reads SER515-Group1-Backend-Repo/.env

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal
from typing import Optional
import models
import schemas
from passlib.context import CryptContext
from schemas import UserCreate, UserResponse
import auth, schemas, models
from auth import create_access_token, verify_access_token


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

print("Test Github Connection")

@app.get("/stories", response_model=list[schemas.StoryResponse])
def get_stories(assignee: Optional[str] = None,db: Session = Depends(get_db)):
    if assignee:
        return db.query(models.UserStory).filter(models.UserStory.assignee == assignee).all()
    return db.query(models.UserStory).all()


@app.post("/stories")
def add_story(request: schemas.StoryCreate, db: Session = Depends(get_db)):
    new_story = models.UserStory(
        title=request.title,
        description=request.description,
        assignee=request.assignee,
        status=request.status
    )
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    return {"message": "Story added successfully", "story": new_story}


#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/users", response_model=schemas.UserResponse)
def create_user(request: schemas.UserCreate, db: Session = Depends(get_db)):
    # Split full name into first and last
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
#def login_json(request: schemas.LoginRequest, db: Session = Depends(get_db)):
def login_json(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    #user = db.query(models.User).filter_by(email=request.email).first()
    user = db.query(models.User).filter_by(email=form_data.username).first()
    #if not user or not pwd_context.verify(request.password, user.password_hash):
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
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