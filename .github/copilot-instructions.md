# AI Coding Agent Instructions - Agile Dashboard Backend

## Project Overview
**Agile Dashboard** is a full-stack Requirements Engineering Tool with:
- **Backend**: FastAPI (Python 3.9+) REST API with JWT authentication, MySQL database, SQLAlchemy ORM
- **Frontend**: React + Vite with ShadCN UI components (lives in sibling repo)
- **Deployment**: Docker Compose orchestrates MySQL, FastAPI backend, and React frontend

## Architecture & Key Components

### Backend Structure (this repo)
| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, all route handlers, status validation logic (539 lines) |
| `models.py` | SQLAlchemy ORM models: `User`, `UserStory` |
| `schemas.py` | Pydantic validation schemas with camelCase aliases via `to_camel_case()` |
| `auth.py` | JWT token creation/verification using `python-jose` |
| `database.py` | SQLAlchemy engine, session factory, connection string |
| `alembic/` | Database migrations (version history tracked in `versions/`) |

### Story Status Workflow (CRITICAL)
Stories follow a strict state machine defined in `main.py`:
```python
VALID_STATUSES = ["Backlog", "Proposed", "Needs Refinement", "In Refinement", "Ready To Commit", "Sprint Ready"]

STATUS_TRANSITIONS = {
    "Backlog": {"Proposed"},
    "Proposed": {"Needs Refinement", "Backlog"},
    "Needs Refinement": {"In Refinement", "Proposed"},
    "In Refinement": {"Ready To Commit", "Needs Refinement"},
    "Ready To Commit": {"Sprint Ready", "In Refinement"},
    "Sprint Ready": {"Ready To Commit"},  # Can only go back
}
```
- Use `ensure_valid_status_or_400()` to validate status values (case-insensitive, returns canonical form)
- Use `validate_status_transition_or_400()` to enforce legal transitions
- Status updates that violate transitions must raise HTTP 400 with detail message listing allowed targets

### Story Data Model
`UserStory` has:
- `assignees`: JSON array of usernames (not single value; use `assignees` in schemas, not `assignee`)
- `tags`: String (stored) but converted to List[str] in response via `parse_tags()` validator
- `story_points`: Fibonacci values only [0, 1, 2, 3, 5, 8, 13, 21] (enforced by `StoryCreate` validator)
- `acceptance_criteria`: JSON array
- `activity`: JSON array (comment/audit log)
- `created_by`, `created_on`: Audit fields

### Authentication & Authorization
- JWT tokens created via `auth.create_access_token(sub=user_email)` → access_token with Bearer type
- `get_current_user()` dependency extracts email from token, validates user exists
- All story mutations (`POST /stories`, `PUT /stories/{id}`, `DELETE`) require authentication
- Queries (`GET /stories`) are **unauthenticated** but can filter by `created_by`, `assignee`, `status`, `tags`, dates

### CORS Configuration
Hardcoded in `main.py` (lines 29-35):
```python
origins = [
    "http://localhost:5173",      # Frontend dev (Vite)
    "http://127.0.0.1:5173",
    "http://localhost:3000",      # Alternative port
    "http://127.0.0.1:3000",
]
```
Add new origins here if frontend changes port.

## Development Workflow

### Local Setup (Without Docker)
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Environment file required
cp .env.example .env
# Set DB_HOST=localhost, DB_DATABASE=agile_db, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Apply migrations
alembic upgrade head

# Run dev server (auto-reloads on file changes)
uvicorn main:app --reload
```
Backend: http://localhost:8000 | Docs: http://localhost:8000/docs

### Docker Setup (Recommended)
```bash
docker-compose up
# MySQL on port 3306, Backend on 8000, both services auto-start
```

### Database Migrations
After schema changes in `models.py`:
```bash
alembic revision --autogenerate -m "Describe change"
alembic upgrade head
```
Migrations live in `alembic/versions/` with timestamps. Always commit migration files.

## Code Patterns & Conventions

### Pydantic Schema Aliases
All schemas use camelCase aliases (for frontend compatibility):
```python
class StoryCreate(BaseModel):
    story_points: Optional[int] = None
    acceptance_criteria: Optional[list] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel_case,  # _snake → camelCase
        populate_by_name=True,          # Accept both forms
    )
```
Frontend sends `storyPoints`, `acceptanceCriteria`; convert via alias.

### Validators in Schemas
Use `@field_validator` with `mode="before"` for input cleaning:
```python
@field_validator("story_points", mode="before")
@classmethod
def validate_story_points(cls, v):
    if v in (None, "", "null"):
        return None
    if isinstance(v, str):
        v = int(v)  # Coerce from string
    if v not in VALID_STORY_POINTS:
        raise ValueError(f"Must be Fibonacci: {VALID_STORY_POINTS}")
    return v
```

### Dependency Injection
FastAPI endpoints use `Depends()` for reusable logic:
```python
@app.post("/stories")
def add_story(
    request: schemas.StoryCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # current_user is authenticated User; db is SQLAlchemy session
```

### Query Filtering Pattern
Multi-valued filters (comma-separated or array) parsed via `parse_multi()`:
```python
def parse_multi(value):
    if not value:
        return None
    raw = value if isinstance(value, list) else value.split(",")
    return [v.strip().lower() for v in raw if v.strip()]

# Usage in /stories endpoint:
# GET /stories?status=backlog,proposed&assignee=alice,bob
status_list = parse_multi(status)  # ["backlog", "proposed"]
query = query.filter(or_(*[func.lower(UserStory.status) == s for s in status_list]))
```

### JSON Queries for Arrays
Filter stories by assignee (JSON array):
```python
from sqlalchemy import func
query = query.filter(func.json_contains(models.UserStory.assignees, f'"{assignee}"'))
```

### Password & User Creation
1. Split full name into first/last on user creation
2. Hash password with `pwd_context.hash()`
3. Verify with `pwd_context.verify(plain, hash)`
4. Check uniqueness: email AND username must be unique

## Critical Gotchas & Testing Points

### Status Validation (Recent Work)
- **Issue #90**: Added validation to every status endpoint; ensure ALL story mutations enforce `validate_status_transition_or_400()`
- Case-insensitive matching; canonical form must be used in DB
- No mutation should bypass transition validation

### Multi-Assignee Migration
- Old code used single `assignee` field; new code uses `assignees` (JSON array)
- Legacy migrations exist; `StoryResponse.parse_assignees()` coerces both formats to list
- Always work with lists when handling assignees

### Tags Handling
- DB stores as comma-separated string; schemas convert to List[str]
- Filtering uses `LIKE` for partial matches (case-insensitive)
- Frontend receives array; send back as comma-separated string in POST

### Story Points (Fibonacci Only)
- Accepted values: `[0, 1, 2, 3, 5, 8, 13, 21]`
- Values > 13 signal story needs splitting
- Any other value raises validation error with the list of valid values

## Integration Points

### Frontend → Backend Communication
- All API calls via Axios (frontend/src/api/axios.js)
- Request body uses camelCase; responses auto-converted via alias
- Auth: Frontend stores JWT in localStorage, sends `Authorization: Bearer {token}` header
- Error responses: Check `response.detail` or `response.message` for user-facing text

### Database Connection
- MySQL 8.0 in Docker (default host: `db` when using docker-compose, `localhost` for local dev)
- Uses PyMySQL (pure-Python driver, no system dependencies)
- Connection string: `mysql+pymysql://root:@{DB_HOST}/{DB_DATABASE}` (no password required locally)
- Session auto-closes via try/finally in `get_db()` dependency

### Environment Variables (`.env` Required)
```
DB_HOST=db              # or localhost for local dev
DB_DATABASE=agile_db
SECRET_KEY=your-secret  # For JWT signing
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Testing & Debugging Tips

1. **Test endpoint in docs**: Navigate to http://localhost:8000/docs → Swagger UI auto-generated from FastAPI
2. **Debug migrations**: `alembic current` shows head revision; check `alembic/versions/` for history
3. **Check token validity**: Decode JWT at https://jwt.io with SECRET_KEY to inspect `sub` (email) and `exp`
4. **MySQL queries**: Port 3306 exposed; connect with `mysql -h localhost -u root agile_db` (no password)
5. **Status transitions**: Test both valid and invalid transitions; endpoint must return 400 with allowed targets
6. **Filter combinations**: AND-ing different filters (status + assignee), OR-ing within same filter (multiple statuses)

---

**Last Updated**: December 2025 | **Current Branch**: #90-Add-Validation-To-Every-Status
