from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import schemas
from passlib.context import CryptContext
from schemas import UserCreate, UserResponse


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
def get_stories(db: Session = Depends(get_db)):

    stories = db.query(models.UserStory).all()
    return stories


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
