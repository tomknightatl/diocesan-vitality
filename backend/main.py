import os
from fastapi import FastAPI
from dotenv import load_dotenv
from supabase import create_client, Client
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

# Load .env file from the project root
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI()

# Configure CORS middleware
origins = [
    "http://usccb.diocesevitality.org",
    "https://usccb.diocesevitality.org",
    "http://localhost:8080",
    "http://localhost:8081",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Check if credentials are set
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not found in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/api")
def read_root():
    return {"message": "Hello from the Python backend!"}

@app.get("/api/summary")
async def get_summary():
    """
    Provides a summary of dioceses and their parish directory URLs.
    """
    try:
        # Fetch all records from DiocesesParishDirectory to calculate summary
        response = supabase.table('DiocesesParishDirectory').select('parish_directory_url').execute()
        data = response.data

        total_dioceses_processed = len(data)
        found_parish_directories = sum(1 for item in data if item['parish_directory_url'] is not None)
        not_found_parish_directories = total_dioceses_processed - found_parish_directories

        return {
            "total_dioceses_processed": total_dioceses_processed,
            "found_parish_directories": found_parish_directories,
            "not_found_parish_directories": not_found_parish_directories
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dioceses")
def get_dioceses():
    """
    Fetches the first 20 records from the 'Dioceses' table.
    """
    try:
        response = supabase.table('Dioceses').select('*').limit(20).execute()
        # The actual data is in response.data
        return response.data
    except Exception as e:
        # In a real app, you'd want more robust error handling and logging
        return {"error": str(e)}