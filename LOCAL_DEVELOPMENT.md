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
- [Syncing Local DEV Database with PRD](#syncing-local-dev-database-with-prd)
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

## Syncing Local DEV Database with PRD

This section provides comprehensive instructions for completely wiping your local development database and replacing it with an exact copy of the production database, including both schema (DDL) and data.

### ⚠️ Critical Warnings

**READ THIS CAREFULLY BEFORE PROCEEDING:**

- **DESTRUCTIVE OPERATION:** This process will completely destroy all data in your local development database
- **NO UNDO:** Once the sync begins, you cannot revert to your previous local data
- **PRODUCTION DATA:** You'll be working with real production data - handle with extreme care
- **BACKUP FIRST:** Always create a backup of your current local database before proceeding
- **CONFIRMATION REQUIRED:** Double-check all commands and credentials before execution
- **ENVIRONMENT ISOLATION:** Ensure you're working in the correct environment (local, not production)

### Prerequisites

Before starting the sync process, ensure you have:

1. **Production Database Credentials:**
   - `SUPABASE_DB_HOST_PRD` - Production database host
   - `SUPABASE_DB_PORT_PRD` - Production database port (typically 5432)
   - `SUPABASE_DB_PASSWORD_PRD` - Production database password
   - Database name (typically `postgres` or your project name)

2. **Local Environment Access:**
   - Docker and Docker Compose installed and running
   - Access to the local database container
   - Sufficient disk space for the backup file (production database size + 20% buffer)

3. **Required Tools:**
   - `pg_dump` and `pg_restore` (included with PostgreSQL client tools)
   - `docker` and `docker-compose` commands
   - Text editor for updating `.env` file if needed

4. **Current Status:**
   - Local development environment should be stopped before starting
   - No active connections to the local database
   - Sufficient time for the operation (depends on database size)

### Step-by-Step Sync Process

#### Step 1: Stop the Local Development Environment

First, ensure all services are stopped to prevent conflicts:

```bash
# Stop all Docker Compose services
docker-compose down

# Verify no containers are running
docker ps
```

**Expected Output:** No containers should be listed (or only unrelated containers).

#### Step 2: Backup Your Current Local Database (Optional but Recommended)

Before wiping your local database, create a backup in case you need to revert:

```bash
# Create a backup directory
mkdir -p ~/backups/diocesan-vitality

# Backup the current local database
docker exec diocesan-vitality-db-1 pg_dump -U postgres -d local_db > ~/backups/diocesan-vitality/local_db_backup_$(date +%Y%m%d_%H%M%S).sql

# Verify the backup was created
ls -lh ~/backups/diocesan-vitality/
```

**Verification:** Check that the backup file exists and has a reasonable size (not empty).

#### Step 3: Create a Fresh Production Database Backup

Create a complete backup of the production database including schema and data:

```bash
# Create backup directory if it doesn't exist
mkdir -p ~/backups/diocesan-vitality

# Export production credentials from .env file
export PRD_DB_HOST=$(grep SUPABASE_DB_HOST_PRD .env | cut -d '=' -f2 | tr -d '"')
export PRD_DB_PORT=$(grep SUPABASE_DB_PORT_PRD .env | cut -d '=' -f2 | tr -d '"')
export PRD_DB_PASSWORD=$(grep SUPABASE_DB_PASSWORD_PRD .env | cut -d '=' -f2 | tr -d '"')
export PRD_DB_NAME="postgres"  # Adjust if your production DB name is different

# Create the production backup with custom format for better restore performance
PGPASSWORD=$PRD_DB_PASSWORD pg_dump -h $PRD_DB_HOST -p $PRD_DB_PORT -U postgres -d $PRD_DB_NAME \
  --format=custom \
  --no-owner \
  --no-acl \
  --verbose \
  --file=~/backups/diocesan-vitality/prd_db_backup_$(date +%Y%m%d_%H%M%S).dump

# Verify the backup was created
ls -lh ~/backups/diocesan-vitality/prd_db_backup_*.dump
```

**Important Notes:**
- The `--format=custom` option creates a compressed backup that's faster to restore
- `--no-owner` and `--no-acl` prevent permission issues during restore
- The backup file will be named with a timestamp for easy identification

**Verification:** Ensure the backup file exists and has a reasonable size (should match your production database size).

#### Step 4: Wipe the Local Database Clean

Completely remove the local database volume and recreate it:

```bash
# Stop all services (if not already stopped)
docker-compose down

# Remove the database volume (this deletes all local data)
docker volume rm diocesan-vitality_local_db_data

# Verify the volume is removed
docker volume ls | grep diocesan-vitality
```

**Expected Output:** No volumes matching `diocesan-vitality` should be listed.

**Safety Check:** If the volume removal fails, ensure no containers are using it:
```bash
# Check for any running containers
docker ps -a | grep diocesan-vitality

# Force stop any remaining containers
docker-compose down -v
```

#### Step 5: Start Fresh Local Database Instance

Start the local database with a clean slate:

```bash
# Start only the database service
docker-compose up -d db

# Wait for the database to be ready (usually 10-30 seconds)
echo "Waiting for database to start..."
sleep 15

# Verify the database is running
docker ps | grep diocesan-vitality-db

# Check database logs for any errors
docker logs diocesan-vitality-db-1 --tail 20
```

**Expected Output:** The database container should be running with no errors in the logs.

#### Step 6: Restore Production Backup to Local Database

Restore the production database backup to your local instance:

```bash
# Get the latest production backup file
LATEST_BACKUP=$(ls -t ~/backups/diocesan-vitality/prd_db_backup_*.dump | head -1)

echo "Restoring from: $LATEST_BACKUP"

# Restore the backup to the local database
docker exec -i diocesan-vitality-db-1 pg_restore -U postgres -d local_db \
  --no-owner \
  --no-acl \
  --verbose \
  < $LATEST_BACKUP

# Verify the restore completed successfully
docker exec diocesan-vitality-db-1 psql -U postgres -d local_db -c "\dt"
```

**Expected Output:** A list of database tables should be displayed, showing the schema was restored successfully.

**Troubleshooting:** If the restore fails, check:
- The backup file is not corrupted
- The local database has sufficient disk space
- The database container is running and accessible

#### Step 7: Verify the Sync Was Successful

Perform comprehensive verification to ensure the sync completed correctly:

```bash
# Check database size
docker exec diocesan-vitality-db-1 psql -U postgres -d local_db -c "SELECT pg_size_pretty(pg_database_size('local_db'));"

# Count tables
docker exec diocesan-vitality-db-1 psql -U postgres -d local_db -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# Check for any critical tables (adjust based on your schema)
docker exec diocesan-vitality-db-1 psql -U postgres -d local_db -c "\dt"

# Sample data verification (replace with your actual table names)
docker exec diocesan-vitality-db-1 psql -U postgres -d local_db -c "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "Table 'users' not found"
docker exec diocesan-vitality-db-1 psql -U postgres -d local_db -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null || echo "Table 'organizations' not found"
```

**Verification Checklist:**
- [ ] Database size matches expected production size
- [ ] All expected tables are present
- [ ] Row counts in critical tables are reasonable
- [ ] No error messages in database logs
- [ ] Database connections work correctly

#### Step 8: Update .env File (If Needed)

If your production database uses different configuration than your local setup, update your `.env` file:

```bash
# Review current .env settings
cat .env | grep SUPABASE

# The local database credentials typically remain:
# SUPABASE_URL_DEV="http://localhost:54322"
# SUPABASE_KEY_DEV="your_local_supabase_key"
# SUPABASE_DB_HOST_DEV="127.0.0.1"
# SUPABASE_DB_PORT_DEV="54322"
# SUPABASE_DB_PASSWORD_DEV="postgres"

# Production credentials should already be set from initial setup
# SUPABASE_URL_PRD="your_production_url"
# SUPABASE_KEY_PRD="your_production_key"
# SUPABASE_DB_HOST_PRD="your_production_host"
# SUPABASE_DB_PORT_PRD="5432"
# SUPABASE_DB_PASSWORD_PRD="your_production_password"
```

**Note:** Local database credentials typically don't need to change after a sync, as you're replacing the data, not the connection configuration.

#### Step 9: Restart the Full Development Stack

Start all services with the newly synced database:

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 20

# Check service status
docker-compose ps

# Check backend health
curl http://localhost:8000/health

# Check frontend accessibility
curl -I http://localhost:3000
```

**Expected Output:** All services should be running and healthy.

#### Step 10: Final Verification and Testing

Perform end-to-end testing to ensure everything works correctly:

```bash
# Test database connection from backend
docker exec diocesan-vitality-backend-1 python -c "
import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(
    host='db',
    port=5432,
    database='local_db',
    user='postgres',
    password='postgres'
)
print('Database connection successful!')
conn.close()
"

# Test API endpoints
curl http://localhost:8000/docs
curl http://localhost:8000/health

# Check application logs for any errors
docker-compose logs --tail=50 backend
docker-compose logs --tail=50 frontend
```

**Final Verification Checklist:**
- [ ] All Docker containers are running
- [ ] Backend health check returns 200 OK
- [ ] Frontend is accessible at localhost:3000
- [ ] API documentation is accessible at localhost:8000/docs
- [ ] No error messages in service logs
- [ ] Database queries work correctly
- [ ] Application functions as expected with production data

### Troubleshooting Common Issues

#### Issue 1: Database Volume Removal Fails

**Symptom:** `docker volume rm` command fails with "volume is in use"

**Solution:**
```bash
# Stop all containers forcefully
docker-compose down -v

# Remove any orphaned containers
docker container prune -f

# Try volume removal again
docker volume rm diocesan-vitality_local_db_data
```

#### Issue 2: Production Backup Fails

**Symptom:** `pg_dump` command fails with connection errors

**Solution:**
```bash
# Verify production credentials are correct
echo $PRD_DB_HOST
echo $PRD_DB_PORT
echo $PRD_DB_PASSWORD

# Test database connection
PGPASSWORD=$PRD_DB_PASSWORD psql -h $PRD_DB_HOST -p $PRD_DB_PORT -U postgres -d postgres -c "SELECT version();"

# Check network connectivity
ping -c 3 $PRD_DB_HOST
telnet $PRD_DB_HOST $PRD_DB_PORT
```

#### Issue 3: Restore Fails with Permission Errors

**Symptom:** `pg_restore` fails with "permission denied" errors

**Solution:**
```bash
# Ensure you're using the correct flags
docker exec -i diocesan-vitality-db-1 pg_restore -U postgres -d local_db \
  --no-owner \
  --no-acl \
  --verbose \
  < $LATEST_BACKUP

# If still failing, try dropping and recreating the database
docker exec diocesan-vitality-db-1 psql -U postgres -c "DROP DATABASE IF EXISTS local_db;"
docker exec diocesan-vitality-db-1 psql -U postgres -c "CREATE DATABASE local_db;"
# Then retry the restore
```

#### Issue 4: Database Connection Issues After Sync

**Symptom:** Application cannot connect to database after sync

**Solution:**
```bash
# Check database container is running
docker ps | grep diocesan-vitality-db

# Check database logs
docker logs diocesan-vitality-db-1 --tail 50

# Test connection from host machine
docker exec -it diocesan-vitality-db-1 psql -U postgres -d local_db -c "SELECT version();"

# Restart the database container
docker-compose restart db

# Restart all services
docker-compose restart
```

#### Issue 5: Insufficient Disk Space

**Symptom:** Backup or restore fails with "no space left on device"

**Solution:**
```bash
# Check disk space
df -h

# Clean up old backups (keep last 3)
cd ~/backups/diocesan-vitality
ls -t prd_db_backup_*.dump | tail -n +4 | xargs rm -f

# Clean up Docker system
docker system prune -a --volumes -f

# Remove unused Docker images
docker image prune -a -f
```

### Safety Precautions and Best Practices

1. **Always Create Backups:**
   - Never skip the local database backup step
   - Keep multiple backup versions (at least 3 recent ones)
   - Store backups in a location separate from your project directory

2. **Test in Isolation:**
   - Perform the sync when you're not actively developing
   - Use a separate branch if you're working on features
   - Notify team members before syncing shared resources

3. **Verify Credentials:**
   - Double-check all production credentials before starting
   - Use environment variables instead of hardcoding passwords
   - Never commit credentials to version control

4. **Monitor Performance:**
   - Large databases may take considerable time to backup and restore
   - Monitor system resources during the operation
   - Perform syncs during off-peak hours if possible

5. **Document Changes:**
   - Keep a log of when syncs were performed
   - Note any issues encountered and how they were resolved
   - Document any schema changes that might affect development

6. **Regular Maintenance:**
   - Clean up old backup files regularly
   - Monitor disk space usage
   - Review and update this process as needed

### Rollback Procedure

If you need to revert to your previous local database:

```bash
# Stop all services
docker-compose down

# Remove the current database volume
docker volume rm diocesan-vitality_local_db_data

# Start a fresh database instance
docker-compose up -d db

# Wait for database to be ready
sleep 15

# Restore your local backup
LATEST_LOCAL_BACKUP=$(ls -t ~/backups/diocesan-vitality/local_db_backup_*.sql | head -1)
docker exec -i diocesan-vitality-db-1 psql -U postgres -d local_db < $LATEST_LOCAL_BACKUP

# Restart all services
docker-compose up -d
```

### Additional Resources

- [PostgreSQL Documentation: pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html)
- [PostgreSQL Documentation: pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html)
- [Docker Volumes Documentation](https://docs.docker.com/storage/volumes/)
- [Supabase Database Management](https://supabase.com/docs/guides/database)

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

- 2026-06-02: Added comprehensive section for syncing local DEV database with PRD, including step-by-step instructions for wiping local database, creating production backups, restoring data, verification procedures, and troubleshooting guidance.
- 2026-05-30: Consolidated `docker-compose.yml` and updated documentation for a streamlined local development setup.