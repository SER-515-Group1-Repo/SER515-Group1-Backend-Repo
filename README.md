# SER515-Group1-Backend-Repo

# Agile Dashboard - Backend

This repository contains the backend API for the Agile Dashboard project. It is a robust RESTful API built with Python and the FastAPI framework, designed to handle user authentication, story management, and data persistence.

---

## ✨ Features

- **FastAPI Framework:** High-performance, asynchronous web framework for building APIs with Python.
- **User Authentication:** JWT-based authentication for securing endpoints. Includes endpoints for user registration and login.
- **CRUD Operations:** Full Create, Read, Update, and Delete functionality for user stories.
- **Database Management:** Uses SQLAlchemy ORM for database interaction and Alembic for schema migrations.
- **Data Validation:** Leverages Pydantic for robust request and response data validation.
- **Dockerized:** Fully containerized for consistent and easy setup across any development environment.

---

## 🛠️ Technology Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** [MySQL](https://www.mysql.com/) v8.0
- **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Authentication:** [python-jose](https://python-jose.readthedocs.io/) (JWT), [passlib](https://passlib.readthedocs.io/) (password hashing)
- **Server:** [Uvicorn](https://www.uvicorn.org/)
- **Containerization:** [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- **AWS RDS:** MySQL Database deployment
- **Render:** Python FastAPI deployment
- **Python Version:** 3.9.6

---

## 🗃️ Database Schema

The application uses a MySQL database named `agile_db` with the following main tables:

#### `users` Table

| Field           | Type           | Constraints                 |
| --------------- | -------------- | --------------------------- |
| `id`            | `int`          | Primary Key, Auto-Increment |
| `username`      | `varchar(250)` | Not Null, Unique            |
| `email`         | `varchar(255)` | Not Null, Unique            |
| `password_hash` | `varchar(255)` | Not Null                    |
| `first_name`    | `varchar(250)` | Not Null                    |
| `last_name`     | `varchar(250)` | Not Null                    |
| `is_active`     | `tinyint(1)`   | Not Null, Default 1         |
| `created_on`    | `datetime`     | Default NOW()               |

#### `stories` Table

| Field                 | Type           | Constraints                     |
| --------------------- | -------------- | ------------------------------- |
| `id`                  | `int`          | Primary Key, Auto-Increment     |
| `title`               | `varchar(250)` | Not Null                        |
| `description`         | `text`         | Not Null                        |
| `assignee`            | `varchar(250)` | Not Null, Default 'Unassigned'  |
| `status`              | `varchar(250)` | Not Null, Default 'In Progress' |
| `tags`                | `varchar(500)` | Nullable                        |
| `created_by`          | `varchar(250)` | Nullable                        |
| `acceptance_criteria` | `json`         | Nullable                        |
| `story_points`        | `int`          | Nullable                        |
| `activity`            | `json`         | Nullable                        |
| `created_on`          | `datetime`     | Default NOW()                   |


---

## 🚀 Deployment URL
**URL:** https://ser515-group1-backend-repo.onrender.com/docs

---

## 📚 Getting Started

This project is designed to be the central control point for running the entire full-stack application via Docker Compose.

### Prerequisites

1.  **Git:** You must have Git installed to clone the repositories.
2.  **Docker & Docker Compose:** You must have Docker Desktop (or Docker Engine with the Compose plugin) installed and running.
    - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Installation and Setup

1.  **Clone both repositories** into a single parent directory.

    ```bash
    # Make sure you are in your main development folder
    git clone git@github.com:SER-515-Group1-Repo/SER515-Group1-Frontend-Repo.git
    git clone git@github.com:SER-515-Group1-Repo/SER515-Group1-Backend-Repo.git
    ```

2.  **Navigate into this backend directory**, as it contains the main `docker-compose.yml` file.

    ```bash
    cd SER515-Group1-Backend-Repo
    ```

3.  **Create the backend environment file.** Copy the example file to create your local `.env` file. This is required for Docker to configure the services.

*   **On macOS / Linux:**
    ```bash
    cp .env.example .env
    ```
*   **On Windows (Command Prompt):**
    ```bash
    copy .env.example .env
    ```

4.  **Create the frontend environment file.** This command creates the `.env` file inside the frontend directory.

*   **On macOS / Linux:**
    ```bash
    cp ../SER515-Group1-Frontend-Repo/.env.example ../SER515-Group1-Frontend-Repo/.env
    ```
*   **On Windows (Command Prompt):**
    ```bash
    copy ..\SER515-Group1-Frontend-Repo\.env.example ..\SER515-Group1-Frontend-Repo\.env
    ```

### Running the Full-Stack Application

From the root of **this directory** (`SER515-Group1-Backend-Repo`), run the following command:

```bash
docker-compose up --build
```

This single command will orchestrate the entire application stack, including building images, starting the database, running migrations, and launching the backend and frontend servers.

---

## 🌐 Accessing the Application

Once the Docker containers are running, you can access the services at the following URLs:

- **Frontend Application:** [**http://localhost:5173**](http://localhost:5173)
- **Backend API Base URL:** [**http://localhost:8000**](http://localhost:8000)
- **Backend Interactive API Docs:** [**http://localhost:8000/docs**](http://localhost:8000/docs)
