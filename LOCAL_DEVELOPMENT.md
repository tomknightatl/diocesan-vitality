# Local Development Environment

This document outlines how to set up and run the application locally using Docker Compose. This setup is designed to mirror the production environment as closely as possible while still being easy to run on a local machine.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Obtaining and Generating Credentials](#obtaining-and-generating-credentials)
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
- Access to Supabase and Google Generative AI credentials for both development and production environments. See "Obtaining and Generating Credentials" below.

## Setup

1.  **Create a `.env` file:**
    Copy the `.env.example` file from the project root to a new file named `.env`:
    ```bash
    cp .env.example .env
    ```

2.  **Update the `.env` file:**
    Open the `.env` file and replace the placeholder values with your actual credentials.

    ```
    SUPABASE_URL_DEV="your_supabase_dev_url"
    SUPABASE_KEY_DEV="your_supabase_dev_key"
    SUPABASE_DB_HOST_DEV="your_supabase_dev_db_host"
    SUPABASE_DB_PORT_DEV="your_supabase_dev_db_port"
    SUPABASE_DB_PASSWORD_DEV="your_supabase_dev_db_password"
    GENAI_API_KEY_DEV="your_genai_dev_api_key"
    SUPABASE_URL_PRD="your_supabase_prod_url"
    SUPABASE_KEY_PRD="your_supabase_prod_key"
    SUPABASE_DB_HOST_PRD="your_supabase_prod_db_host"
    SUPABASE_DB_PORT_PRD="your_supabase_prod_db_port"
    SUPABASE_DB_PASSWORD_PRD="your_supabase_prod_db_password"
    GENAI_API_KEY_PRD="your_genai_prod_api_key"
    ```

## Obtaining and Generating Credentials

This section provides instructions on how to acquire the necessary API keys and credentials for both local development and production administrative tasks.

### Supabase Development Credentials

These credentials are for your local Supabase instance, which you start using `supabase start`.

*   **`SUPABASE_URL_DEV` & `SUPABASE_KEY_DEV` (Application API):**
    1.  Run `supabase start` in your project's `supabase` directory.
    2.  In the output, locate "Project URL" (for `SUPABASE_URL_DEV`) and "Secret" (for `SUPABASE_KEY_DEV`). The "Secret" key is the service role key and should be used for backend operations.
*   **`SUPABASE_DB_HOST_DEV` & `SUPABASE_DB_PORT_DEV` & `SUPABASE_DB_PASSWORD_DEV` (Direct Database Access):**
    1.  These are for direct connections to your local PostgreSQL database.
    2.  Default values are: Host `127.0.0.1`, Port `54322`, Password `postgres`.

### Supabase Production Credentials

These credentials are for your live production Supabase project. Handle them with extreme care.

*   **`SUPABASE_URL_PRD` & `SUPABASE_KEY_PRD` (Application API):**
    1.  Go to your Supabase Dashboard ([app.supabase.com](https://app.supabase.com/)).
    2.  Select your production project.
    3.  Navigate to "Project Settings" -> "API Keys -> Legacy anon, service_role API keys".
    4.  `SUPABASE_KEY_PRD` is the "Service Role (secret)" key. **WARNING: This key has elevated privileges; do not expose it client-side.**
    5.  `SUPABASE_URL_PRD` is the "Project URL".
*   **`SUPABASE_DB_HOST_PRD`, `SUPABASE_DB_PORT_PRD`, & `SUPABASE_DB_PASSWORD_PRD` (Direct Database Access):**
    The database password for production is not directly viewable in the Supabase UI for security reasons. If you do not have it, you will need to reset it.

    **To Obtain Database Credentials:**
    1.  **Log in to your Supabase Dashboard:** Go to [https://app.supabase.com/](https://app.supabase.com/) and log in to your account.
    2.  **Select your Project:** From the list of projects, select the project for which you need the production credentials.
    3.  **Navigate to Database Connection Settings:**
        *   On the top bar, click on the **"Connect"** icon (it looks like a plug, usually near "SQL Editor" and "AI Assistant").
        *   Alternatively, you might find connection details under **"Project Settings"** -> **"Database"**.
    4.  **Locate Connection String:**
        *   Within the "Connect" section, look for "Connection String" or "Connection Info".
        *   You will typically find options for "Direct Connection" and "Connection Pooling". The "Session Pooler connection string" is often recommended for applications.
        *   Copy the connection string. It will look something like: `postgres://postgres.[YOUR_PROJECT_REF]:[YOUR_PASSWORD]@[YOUR_HOST]:5432/postgres`
    5.  **Extract Host and Port:**
        *   From the connection string, identify the host (e.g., `[YOUR_HOST]`) for `SUPABASE_DB_HOST_PRD` and the port (e.g., `5432`) for `SUPABASE_DB_PORT_PRD`.
    6.  **Retrieve/Reset Database Password:**
        *   If you do not have your database password saved, navigate to **"Project Settings"** -> **"Database"**.
        *   Under the "Database Password" section, you will find an option to reset your password. Reset it and save the new password securely. This will be your `SUPABASE_DB_PASSWORD_PRD`.

### Google Generative AI API Key

*   **`GENAI_API_KEY_DEV` & `GENAI_API_KEY_PRD`:**
    1.  Go to Google AI Studio ([aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)) or Google Cloud Console.
    2.  Create a new API key.
    3.  It is recommended to create separate keys for development and production environments, and restrict their usage (e.g., by IP address or API restrictions) as much as possible.

## Connecting to Production Services for Admin Tasks

For certain administrative or maintenance tasks, you may need to connect your local environment to remote production services. This should be done with extreme caution. The credentials for this are managed in the `.env` file created in the Setup section, which is ignored by Git. Ensure you have replaced the placeholder values for `SUPABASE_URL_PRD`, `SUPABASE_KEY_PRD`, `SUPABASE_DB_HOST_PRD`, `SUPABASE_DB_PORT_PRD`, `SUPABASE_DB_PASSWORD_PRD`, and `GENAI_API_KEY_PRD` with your actual production credentials.

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