import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta

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

        # Aggregate data by date with dual granularity
        time_series_data = {}
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

        for col in date_cols:
            df_col = df.dropna(subset=[col]) # Ensure no NaT values

            # Split data into recent and old
            df_old = df_col[df_col[col] < cutoff_date]
            df_recent = df_col[df_col[col] >= cutoff_date]

            # Resample old data by day
            old_counts = df_old.set_index(col).resample('D').size()

            # Resample recent data by hour (using 'h' to avoid deprecation warning)
            recent_counts = df_recent.set_index(col).resample('h').size()

            # Combine and calculate cumulative sum
            combined_counts = pd.concat([old_counts, recent_counts]).sort_index()
            cumulative_counts = combined_counts.cumsum()
            
            # Create final DataFrame for plotting
            df_ts = pd.DataFrame({'date': cumulative_counts.index, 'count': cumulative_counts.values})
            time_series_data[col] = df_ts

        return df, time_series_data

    except Exception as e:
        print(f"Error fetching or processing data from {table_name}: {e}")
        return None, None

def plot_time_series(time_series_data: dict, table_name: str):
    """Generates and saves time-series plots for record counts."""
    if not time_series_data:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    
    min_date, max_date = None, None

    for col_name, df_ts in time_series_data.items():
        ax.plot(df_ts['date'], df_ts['count'], marker='o', linestyle='-', label=f'Records by {col_name}')
        
        # Update min and max dates
        if not df_ts.empty:
            current_min = df_ts['date'].min()
            current_max = df_ts['date'].max()
            if min_date is None or current_min < min_date:
                min_date = current_min
            if max_date is None or current_max > max_date:
                max_date = current_max

    # Set x-axis limits with a 10-day padding
    if min_date and max_date:
        from datetime import timedelta
        ax.set_xlim(min_date - timedelta(days=10), max_date + timedelta(days=10))

    ax.set_title(f'Number of Records in {table_name} Over Time')
    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Number of Records', fontsize=14)
    ax.grid(True)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = f"frontend/public/{table_name.lower()}_records_over_time.png"
    plt.savefig(filename)
    print(f"Chart saved to {filename}")
    plt.close(fig) # Close the figure to free memory

def main():
    tables_to_report = ['Dioceses', 'DiocesesParishDirectory', 'Parishes', 'Parishes']
    
    for table_name in tables_to_report:
        df, time_series_data = fetch_and_process_table(table_name, supabase)
        
        if df is not None:
            print(f"Current number of records in {table_name}: {len(df)}")
            if time_series_data:
                plot_time_series(time_series_data, table_name)
            print("-" * 50)

if __name__ == "__main__":
    main()
