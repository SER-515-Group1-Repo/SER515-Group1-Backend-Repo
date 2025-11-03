# Run Instructions

## Backend (FastAPI)

1. cd backend
2. python -m venv venv
3. source venv/bin/activate (Windows: venv\Scripts\activate)
4. pip install fastapi uvicorn sqlalchemy pydantic
5. uvicorn main:app --reload

Backend runs at http://127.0.0.1:8000  
Docs at http://127.0.0.1:8000/docs

## Frontend (React + Vite)

1. cd frontend
2. npm install
3. npm run dev

Frontend runs at http://localhost:5173

## Notes

- Python 3.9+ and Node 18+ required
- Update CORS origin in main.py if needed
- Run backend and frontend in separate terminals
- Install Requirements using this command: pip install -r requirements.txt
- To start Backend command: uvicorn main:app --reload

## Migration

- To create migration: alembic revision --autogenerate -m "Your message"
- To apply latest migration: alembic upgrade head
