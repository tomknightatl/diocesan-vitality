# Local Development Environment

This document outlines how to set up and run the application locally using Docker Compose. This setup is designed to mirror the production environment as closely as possible while still being easy to run on a local machine.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Local Environment with Docker Compose](#running-the-local-environment-with-docker-compose)
- [Accessing the Application](#accessing-the-application)
- [Service Details](#service-details)
  - [Backend](#backend)
  - [Frontend](#frontend)
  - [Database](#database)
  - [Pipeline](#pipeline)
- [Stopping the Application](#stopping-the-application)
- [Database Management](#database-management)
- [Running the Frontend Natively (Without Docker)](#running-the-frontend-natively-without-docker)
- [See Also](#see-also)
- [Historical Revisions](#historical-revisions)

## Prerequisites

- Docker and Docker Compose
- Access to the development Supabase instance credentials (`DEV_SUPABASE_URL`, `DEV_SUPABASE_KEY`)
- A Google Generative AI API key (`DEV_GENAI_API_KEY`)

## Setup

1.  **Create a `.env` file:**
    Copy the `.env.example` file to a new file named `.env`:
    ```bash
    cp .env.example .env
    ```

2.  **Update the `.env` file:**
    Open the `.env` file and replace the placeholder values with your actual credentials.

    ```
    DEV_SUPABASE_URL="your_dev_supabase_url"
    DEV_SUPABASE_KEY="your_dev_supabase_key"
    DEV_GENAI_API_KEY="your_genai_api_key"
    ```

## Running the Local Environment with Docker Compose

The `docker-compose.yml` file is configured to run the entire application stack locally. It includes services for the backend, frontend, and database.

1.  **Build and start the services:**
    Use the following command to build the Docker images and start the `frontend`, `backend`, and `db` services:
    ```bash
    docker-compose up --build
    ```
    This command will also create a Docker volume to persist database data.

2.  **Live Reloading:**
    The `backend` and `frontend` services are configured with volumes that mount the local source code into the containers. This enables live reloading, so changes you make to the code will be reflected in the running containers without needing to rebuild the images.

## Accessing the Application

Once the services are running, you can access them at the following addresses:

-   **Frontend:** [http://localhost:3000](http://localhost:3000)
-   **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs)
-   **Database:** The `db` service is accessible on `localhost:5433`.

## Service Details

### Backend

The backend service is a FastAPI application.

-   **Location:** The backend code is located in the `backend/` directory.
-   **Dockerfile:** The Docker image is built using `backend/Dockerfile`.
-   **Dependencies:** Python dependencies are listed in `backend/requirements.txt`.
-   **API Documentation:** Once the backend is running, you can access the interactive API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).
-   **Health Check:** The backend has a health check endpoint at [http://localhost:8000/health](http://localhost:8000/health).

### Frontend

The frontend is a React application served by Nginx.

-   **Location:** The frontend code is located in the `frontend/` directory.
-   **Dockerfile:** The Docker image is built using `frontend/Dockerfile`.
-   **Dependencies:** Node.js dependencies are listed in `frontend/package.json`.

### Database

The backend connects to a PostgreSQL database service named `db`.

-   **Database Name:** `local_db`
-   **Username:** `postgres`
-   **Password:** `postgres`
-   **Host (from backend container):** `db`
-   **Port (from backend container):** `5432`
-   **Host (from host machine):** `localhost`
-   **Port (from host machine):** `5433`
-   **Connection String:** `postgresql://postgres:postgres@db:5432/local_db`

The database is initialized with the schema from `sql/initial_schema.sql`.

### Pipeline

The `pipeline` service is not started by default. To run the pipeline, use the `pipeline` profile:

```bash
docker-compose up --build --profile pipeline
```

## Stopping the Application

To stop the services, press `Ctrl+C` in the terminal where `docker-compose` is running. To stop and remove the containers, use:

```bash
docker-compose down
```

## Database Management

The `db` service uses a Docker volume (`diocesan-vitality_local_db_data`) to persist data between runs. To start with a clean database, you can remove the volume:

```bash
docker volume rm diocesan-vitality_local_db_data
```

## Running the Frontend Natively (Without Docker)

This section describes how to run the frontend application directly on your local machine without using Docker. This is useful for frontend-specific development and debugging.

### Prerequisites

-   [Node.js](https://nodejs.org/) (v18 or later recommended) and npm.

### Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    Use npm to install the project's dependencies.
    ```bash
    npm install
    ```

### Running the Application

1.  **Start the development server:**
    ```bash
    npm run dev
    ```
    This will start the Vite development server, and you should see output indicating the server is running, typically on `http://localhost:5173`.

2.  **Access the application:**
    Open your web browser and navigate to the URL provided in the terminal (e.g., `http://localhost:5173`).

### Backend Dependency

The frontend application expects the backend API to be running on `http://localhost:8000`. The Vite configuration is set up to proxy API requests from the frontend to this address.

If you are not running the backend locally via the Docker setup described above, you will need to run the backend separately for API calls to function correctly.

## See Also

- [README.md](README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Historical Revisions

- 2026-05-30: Consolidated `docker-compose.yml` and updated documentation for a streamlined local development setup.
