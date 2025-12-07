# Deploying the backend to Render

This document provides steps to create a Render Web Service for the backend and connect it to a managed database.

1) Add a managed Postgres DB in Render (recommended):
   - Create a Database → Postgres service in Render.
   - After it’s created, copy the `DATABASE_URL` from the Render DB dashboard.

2) Create a New Web Service in Render
   - New → Web Service
   - Connect the `SER515-Group1-Backend-Repo` repository and choose `main`.
   - Build/Start: Use the Dockerfile (Render will run the Dockerfile) and set the start command to `./entrypoint.sh`.
   - Add environment variables:
     - `DATABASE_URL` (value copied from the Postgres DB in step 1)
     - `SECRET_KEY` (a random strong string), mark as secure.
     - Optionally `ALGORITHM` (HS256) and `ACCESS_TOKEN_EXPIRE_MINUTES` (30)
   - Expose port: Render automatically sets an environment variable `PORT` that we use inside `entrypoint.sh`.

3) CORS and Frontend link:
   - After Web Service is created, copy backend URL: `https://<your-backend>.onrender.com`.
   - Set `VITE_BASE_URL` in the Frontend Render Service to this backend URL.
   - Update backend CORS origins to include the frontend URL (or read `FRONTEND_ORIGINS` as env var).

4) Migrations and Running:
   - The entrypoint script runs `alembic upgrade head` automatically.
   - You can watch the Render logs to confirm successful migrations and server start.

5) Notes and Optional configurations
   - If you prefer MySQL instead of Postgres, create the MySQL DB externally or host elsewhere and set `DATABASE_URL` to the MySQL connection string. The app will still use SQLAlchemy’s engine from the URL.
   - If you have a custom domain for the backend, configure it in Render and enable HTTPS.
