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
from auth import create_access_token

app = FastAPI(title="Requirements Engineering Tool Prototype")


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


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/users", response_model=UserResponse)
def create_user(request: UserCreate, db: Session = Depends(get_db)):
    hashed = pwd_context.hash(request.password)
    user = models.User(email=request.email, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/logout")
def logout():
    """
    Dummy logout endpoint – client should discard its JWT.
    """
    return {"message": "Successfully logged out"}

