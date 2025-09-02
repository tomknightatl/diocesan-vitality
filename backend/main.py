import os
from fastapi import FastAPI
from dotenv import load_dotenv
from supabase import create_client, Client
from pathlib import Path

# Load .env file from the project root
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Check if credentials are set
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not found in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/api")
def read_root():
    return {"message": "Hello from the Python backend!"}

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