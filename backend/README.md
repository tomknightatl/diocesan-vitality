# Backend API

This directory contains the FastAPI backend for the USCCB Diocese Vitality Index application.

## Local Development

### 1. Set up Environment

This service requires Python and a virtual environment. Ensure the root `.env` file is populated with your Supabase credentials.

### 2. Install Dependencies

Install the required Python packages using pip:

```sh
pip install -r requirements.txt
```

### 3. Run the Development Server

To start the Uvicorn development server, run the following command from this directory:

```sh
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
