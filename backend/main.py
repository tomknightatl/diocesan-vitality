import os
from fastapi import FastAPI
from dotenv import load_dotenv
# from supabase import create_client, Client

load_dotenv()

app = FastAPI()

# SUPABASE_URL = os.environ.get("SUPABASE_URL")
# SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/api")
def read_root():
    return {"message": "Hello from the Python backend!"}

# Example of a Supabase query
# @app.get("/api/items")
# def get_items():
#     # Replace 'your_table_name' with your actual table name
#     # data, count = supabase.table('your_table_name').select('*').execute()
#     # return data
