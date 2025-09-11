import os
from fastapi import FastAPI, HTTPException
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
    "http://localhost:5173",
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
def get_dioceses(
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "Name",
    sort_order: str = "asc",
    search_query: str = None
):
    """
    Fetches records from the 'Dioceses' table with pagination, sorting, and filtering.
    """
    try:
        offset = (page - 1) * page_size
        
        query = supabase.table('Dioceses').select('*')

        # Apply filtering
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.or_(
                f"Name.ilike.{search_pattern},"
                f"Address.ilike.{search_pattern},"
                f"Website.ilike.{search_pattern}"
            )

        # Apply sorting
        if sort_order.lower() == "desc":
            query = query.order(sort_by, desc=True)
        else:
            query = query.order(sort_by, desc=False)

        # Apply pagination
        response = query.range(offset, offset + page_size - 1).execute()
        dioceses = response.data

        # For each diocese, fetch additional data
        for diocese in dioceses:
            # Get parish directory URL
            # Get parish directory URL (temporary debug: fetch all and filter in Python)
            all_dir_response = supabase.table('DiocesesParishDirectory').select('diocese_id, parish_directory_url').execute()
            matching_dir = next((item for item in all_dir_response.data if item['diocese_id'] == diocese['id']), None)
            diocese['parish_directory_url'] = matching_dir['parish_directory_url'] if matching_dir else None

            # Get count of parishes in the database
            count_response = supabase.table('Parishes').select('count', count='exact').eq('diocese_url', diocese['Website']).execute()
            diocese['parishes_in_db_count'] = count_response.count

        # To get total count for pagination metadata (with filter applied)
        count_query = supabase.table('Dioceses').select('count', count='exact')
        if search_query:
            search_pattern = f"%{search_query}%"
            count_query = count_query.or_(
                f"Name.ilike.{search_pattern},"
                f"Address.ilike.{search_pattern},"
                f"Website.ilike.{search_pattern}"
            )
        count_response = count_query.execute()
        total_count = count_response.count

        return {
            "data": dioceses,
            "total_count": total_count,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dioceses/{diocese_id}")
def get_diocese(diocese_id: int):
    """
    Fetches a single diocese by its ID.
    """
    try:
        response = supabase.table('Dioceses').select('*').eq('id', diocese_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Diocese not found")
        return {"data": response.data[0]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dioceses/{diocese_id}/parishes")
def get_parishes_for_diocese(diocese_id: int):
    """
    Fetches all parishes for a given diocese ID.
    """
    try:
        # First, get the diocese's website using its ID
        diocese_response = supabase.table('Dioceses').select('Website').eq('id', diocese_id).execute()
        if not diocese_response.data:
            raise HTTPException(status_code=404, detail="Diocese not found")
        diocese_website = diocese_response.data[0]['Website']

        parishes_response = supabase.table('Parishes').select('*').eq('diocese_url', diocese_website).execute()
        parishes = parishes_response.data

        # For each parish, fetch reconciliation and adoration facts
        for parish in parishes:
            # For each parish, fetch reconciliation and adoration facts from ParishData
            reconciliation_response = supabase.table('ParishData').select('fact_value').eq('parish_id', parish['id']).eq('fact_type', 'ReconciliationSchedule').execute()
            parish['reconciliation_facts'] = reconciliation_response.data[0]['fact_value'] if reconciliation_response.data else None

            adoration_response = supabase.table('ParishData').select('fact_value').eq('parish_id', parish['id']).eq('fact_type', 'AdorationSchedule').execute()
            parish['adoration_facts'] = adoration_response.data[0]['fact_value'] if adoration_response.data else None

        return {"data": parishes}
    except Exception as e:
        return {"error": str(e)}
