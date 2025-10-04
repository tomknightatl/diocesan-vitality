import os
from datetime import datetime, timedelta, timezone

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv

from supabase import Client, create_client

# Load environment variables
load_dotenv()


# Initialize Supabase client (deferred)
def get_supabase_client():
    """Create and return Supabase client with proper error handling."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key or supabase_url == "<url>" or supabase_key == "<key>":
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set with valid values")

    return create_client(supabase_url, supabase_key)


def fetch_and_process_table(table_name: str, supabase_client: Client):
    """Fetches data from a Supabase table and processes it for charting."""
    print(f"Fetching data from {table_name}...")
    try:
        response = supabase_client.table(table_name).select("*").execute()
        data = response.data
        if not data:
            print(f"No data found in {table_name}.")
            return None, None

        df = pd.DataFrame(data)

        # Convert relevant columns to datetime
        date_cols = []
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
            date_cols.append("created_at")
        if "updated_at" in df.columns:
            df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True, errors="coerce")
            date_cols.append("updated_at")
        if "extracted_at" in df.columns:
            df["extracted_at"] = pd.to_datetime(df["extracted_at"], format="ISO8601", utc=True, errors="coerce")
            date_cols.append("extracted_at")
        if "scraped_at" in df.columns:  # For ParishSchedules
            df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")
            date_cols.append("scraped_at")

        if not date_cols:
            print(f"No relevant date columns found in {table_name} for time-series analysis.")
            return df, None

        # Exclude 'created_at' for specific tables as per request
        if table_name in ["Dioceses", "Parishes"] and "created_at" in date_cols:
            date_cols.remove("created_at")

        # For ParishData, prioritize updated_at over created_at since schedule extractions update existing records
        if table_name == "ParishData" and "updated_at" in date_cols and "created_at" in date_cols:
            date_cols.remove("created_at")

        # Aggregate data by date with dual granularity
        time_series_data = {}
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

        for col in date_cols:
            df_col = df.dropna(subset=[col])  # Ensure no NaT values

            # Split data into recent and old
            df_old = df_col[df_col[col] < cutoff_date]
            df_recent = df_col[df_col[col] >= cutoff_date]

            # Resample old data by day
            old_counts = df_old.set_index(col).resample("D").size()

            # Resample recent data by hour (using 'h' to avoid deprecation warning)
            recent_counts = df_recent.set_index(col).resample("h").size()

            # Combine and calculate cumulative sum
            combined_counts = pd.concat([old_counts, recent_counts]).sort_index()
            cumulative_counts = combined_counts.cumsum()

            # Create final DataFrame for plotting
            df_ts = pd.DataFrame({"date": cumulative_counts.index, "count": cumulative_counts.values})
            time_series_data[col] = df_ts

        return df, time_series_data

    except Exception as e:
        print(f"Error fetching or processing data from {table_name}: {e}")
        return None, None


def plot_time_series(
    time_series_data: dict, table_name: str, global_min_date: datetime, global_max_date: datetime, y_max_limits: dict
):
    """Generates and saves time-series plots for record counts."""
    if not time_series_data:
        return

    # Create responsive figure size that works well in Bootstrap cards
    fig, ax = plt.subplots(figsize=(10, 6))

    # Set font sizes to match page text - no smaller than body text (14px)
    plt.rcParams.update(
        {
            "font.size": 14,  # Base font size to match page text
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        }
    )

    # Use professional colors
    colors = ["#007bff", "#6c757d", "#28a745", "#dc3545", "#ffc107", "#17a2b8"]

    for i, (col_name, df_ts) in enumerate(time_series_data.items()):
        color = colors[i % len(colors)]
        ax.plot(
            df_ts["date"],
            df_ts["count"],
            marker="o",
            linestyle="-",
            color=color,
            linewidth=2,
            markersize=4,
            label=f'Records by {col_name.replace("_", " ").title()}',
        )

    # Set x-axis limits using global min/max dates
    if global_min_date and global_max_date:
        ax.set_xlim(global_min_date, global_max_date)

    # Set y-axis limits: start at 0, end at appropriate max value
    if table_name in y_max_limits:
        ax.set_ylim(0, y_max_limits[table_name])

    # Format y-axis to show only integers (no decimals)
    from matplotlib.ticker import MaxNLocator

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Custom titles for each chart
    custom_titles = {
        "Dioceses": "Dioceses",
        "DiocesesParishDirectory": "Dioceses with a Parish Directory",
        "Parishes": "Parishes Extracted from their Diocese's Parish Directory",
        "ParishData": "Parishes with Adoration or Reconcilation Schedules Extracted from their Website",
    }

    # Use font sizes matching page text - minimum 14px
    chart_title = custom_titles.get(table_name, f"Number of Records in {table_name} Over Time")
    ax.set_title(chart_title, fontsize=16, fontweight="bold", pad=15)
    # Remove axis labels as requested
    ax.set_xlabel("")
    ax.set_ylabel("")

    # Style the grid to be subtle
    ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
    ax.set_facecolor("#fafafa")

    # Remove legend as requested
    # ax.legend(fontsize=14, loc='upper left', frameon=True,
    #           fancybox=True, shadow=True, framealpha=0.9)

    # Add text label showing the most recent data point value
    for i, (col_name, df_ts) in enumerate(time_series_data.items()):
        if not df_ts.empty:
            latest_date = df_ts["date"].iloc[-1]
            latest_count = df_ts["count"].iloc[-1]
            color = colors[i % len(colors)]

            # Position the label near the end of the line
            ax.annotate(
                f"{latest_count:,}",
                xy=(latest_date, latest_count),
                xytext=(10, 5),
                textcoords="offset points",
                fontsize=14,
                fontweight="bold",
                color=color,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=color, alpha=0.8),
            )

    # Format dates on x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.tick_params(axis="x", rotation=45, labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    # Remove top and right spines for cleaner look
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")

    # Use consistent subplot positioning instead of tight_layout for alignment
    plt.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.25)

    # Only save charts if frontend/public directory exists (local development)
    # In Kubernetes pods, this directory doesn't exist and charts are not needed
    output_dir = "frontend/public"
    if os.path.exists(output_dir):
        filename = f"{output_dir}/{table_name.lower()}_records_over_time.png"
        # Save with higher DPI for crisp display on modern screens
        plt.savefig(filename, dpi=150, bbox_inches=None, facecolor="white", edgecolor="none")
        print(f"Chart saved to {filename}")
    else:
        print(f"Skipping chart save (frontend/public directory not found - running in Kubernetes)")

    plt.close(fig)  # Close the figure to free memory


def main():
    try:
        supabase = get_supabase_client()
    except ValueError as e:
        print(f"Warning: Cannot create Supabase client: {e}")
        print("Skipping statistics reporting due to missing credentials.")
        return

    tables_to_report = ["Dioceses", "DiocesesParishDirectory", "Parishes", "ParishData"]

    all_min_dates = []
    all_max_dates = []
    all_time_series_data = {}

    for table_name in tables_to_report:
        df, time_series_data = fetch_and_process_table(table_name, supabase)

        if df is not None:
            print(f"Current number of records in {table_name}: {len(df)}")
            if time_series_data:
                all_time_series_data[table_name] = time_series_data
                for col_name, df_ts in time_series_data.items():
                    if not df_ts.empty:
                        all_min_dates.append(df_ts["date"].min())
                        all_max_dates.append(df_ts["date"].max())
            print("-" * 50)

    global_min_date = min(all_min_dates) if all_min_dates else None
    global_max_date = max(all_max_dates) if all_max_dates else None

    # Add 1 day padding
    if global_min_date:
        global_min_date -= timedelta(days=1)
    if global_max_date:
        global_max_date += timedelta(days=1)

    # Calculate max values for y-axis alignment dynamically
    max_parish_related_count = 0

    for table_name, time_series_data in all_time_series_data.items():
        for col_name, df_ts in time_series_data.items():
            if not df_ts.empty:
                if table_name in ["Parishes", "ParishData"]:
                    max_parish_related_count = max(max_parish_related_count, df_ts["count"].max())

    # Add a buffer to the max value
    y_max_parish_related = max_parish_related_count * 1.1 if max_parish_related_count > 0 else 100  # 10% buffer, min 100

    y_max_limits = {
        "Dioceses": 200,  # These can remain static or be made dynamic if needed
        "DiocesesParishDirectory": 200,  # These can remain static or be made dynamic if needed
        "Parishes": y_max_parish_related,
        "ParishData": y_max_parish_related,
    }

    for table_name, time_series_data in all_time_series_data.items():
        plot_time_series(time_series_data, table_name, global_min_date, global_max_date, y_max_limits)


if __name__ == "__main__":
    main()
