import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

def fetch_and_process_table(table_name: str, supabase_client: Client):
    """Fetches data from a Supabase table and processes it for charting."""
    print(f"Fetching data from {table_name}...")
    try:
        response = supabase_client.table(table_name).select('*').execute()
        data = response.data
        if not data:
            print(f"No data found in {table_name}.")
            return None, None

        df = pd.DataFrame(data)

        # Convert relevant columns to datetime
        date_cols = []
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], utc=True, errors='coerce')
            date_cols.append('created_at')
        if 'extracted_at' in df.columns:
            df['extracted_at'] = pd.to_datetime(df['extracted_at'], format='ISO8601', utc=True, errors='coerce')
            date_cols.append('extracted_at')
        if 'scraped_at' in df.columns: # For ParishSchedules
            df['scraped_at'] = pd.to_datetime(df['scraped_at'], utc=True, errors='coerce')
            date_cols.append('scraped_at')

        if not date_cols:
            print(f"No relevant date columns found in {table_name} for time-series analysis.")
            return df, None

        # Aggregate data by date
        time_series_data = {}
        for col in date_cols:
            # Group by date and count records
            daily_counts = df.set_index(col).resample('D').size().rename('count')
            time_series_data[col] = daily_counts.reset_index().rename(columns={col: 'date'})

        return df, time_series_data

    except Exception as e:
        print(f"Error fetching or processing data from {table_name}: {e}")
        return None, None

def plot_time_series(time_series_data: dict, table_name: str):
    """Generates and saves time-series plots for record counts."""
    if not time_series_data:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    
    for col_name, df_ts in time_series_data.items():
        ax.plot(df_ts['date'], df_ts['count'], marker='o', linestyle='-', label=f'Records by {col_name}')

    ax.set_title(f'Number of Records in {table_name} Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Number of Records')
    ax.grid(True)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = f"reports/{table_name.lower()}_records_over_time.png"
    plt.savefig(filename)
    print(f"Chart saved to {filename}")
    plt.close(fig) # Close the figure to free memory

def main():
    tables_to_report = ['Dioceses', 'DiocesesParishDirectory', 'Parishes', 'ParishSchedules']
    
    for table_name in tables_to_report:
        df, time_series_data = fetch_and_process_table(table_name, supabase)
        
        if df is not None:
            print(f"Current number of records in {table_name}: {len(df)}")
            if time_series_data:
                plot_time_series(time_series_data, table_name)
            print("-" * 50)

if __name__ == "__main__":
    main()
