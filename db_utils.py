import sqlite3
import pandas as pd

def connect_db(db_path):
    """
    Connects to the SQLite database at db_path.

    Args:
        db_path (str): The path to the SQLite database file.

    Returns:
        sqlite3.Connection: The connection object or None if connection fails.
    """
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_path}: {e}")
        return None

def get_db_summary(conn):
    """
    Gets a summary of the database, including table names and row counts.

    Args:
        conn (sqlite3.Connection): The database connection object.

    Returns:
        str: A human-readable string summarizing the database contents.
    """
    if not conn:
        return "No database connection."

    summary_lines = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            return "No tables found in the database."

        summary_lines.append("Database Summary:")
        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                summary_lines.append(f"  Table: {table_name} - Rows: {count}")
            except sqlite3.Error as e:
                summary_lines.append(f"  Table: {table_name} - Error counting rows: {e}")
        return "\n".join(summary_lines)
    except sqlite3.Error as e:
        return f"Error querying sqlite_master: {e}"

def get_table_details(conn, table_name, limit=5):
    """
    Fetches details (a few rows) from a specific table.

    Args:
        conn (sqlite3.Connection): The database connection object.
        table_name (str): The name of the table to query.
        limit (int, optional): The maximum number of rows to fetch. Defaults to 5.

    Returns:
        pandas.DataFrame or tuple: A pandas DataFrame with the table data if pandas is available,
                                   otherwise a tuple containing a list of tuples (rows)
                                   and a list of column names. Returns None on error.
    """
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        try:
            # Try to use pandas for nice formatting
            return pd.DataFrame(rows, columns=column_names)
        except ImportError:
            # Fallback if pandas is not available
            return rows, column_names
    except sqlite3.Error as e:
        print(f"Error fetching details for table {table_name}: {e}")
        return None

def display_database_status(db_path="data.db", show_details=False, tables_to_show=None, limit_details=5):
    """
    Main function to display database status, summary, and optionally table details.

    Args:
        db_path (str, optional): Path to the database file. Defaults to "data.db".
        show_details (bool, optional): Whether to show details for tables. Defaults to False.
        tables_to_show (list, optional): A list of specific table names to show details for.
                                         If None, and show_details is True, details for all tables are shown.
                                         Defaults to None.
        limit_details (int, optional): The number of rows to display for each table's details.
                                       Defaults to 5.
    """
    conn = connect_db(db_path)
    if not conn:
        # connect_db already prints an error
        return

    try:
        print(f"Connecting to database: {db_path}")
        summary = get_db_summary(conn)
        print(summary)

        if show_details:
            print("\nTable Details:")
            tables_to_query = tables_to_show
            if tables_to_query is None:
                # Get all table names if specific ones aren't provided
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables_to_query = [row[0] for row in cursor.fetchall()]
                except sqlite3.Error as e:
                    print(f"Error fetching list of all tables: {e}")
                    tables_to_query = [] # Avoid further errors

            if not tables_to_query:
                print("  No tables specified or found to show details for.")
            else:
                for table_name in tables_to_query:
                    print(f"\n  Details for table {table_name} (limit {limit_details}):")
                    details = get_table_details(conn, table_name, limit=limit_details)
                    if details is not None:
                        if isinstance(details, tuple): # Fallback mode (list of tuples, column_names)
                            rows, colnames = details
                            if rows:
                                print(f"    Columns: {', '.join(colnames)}")
                                for row_idx, row in enumerate(rows):
                                    print(f"      Row {row_idx + 1}: {row}")
                            else:
                                print("    No data found in this table.")
                        else: # pandas DataFrame
                            if not details.empty:
                                print(details.to_string(index=False))
                            else:
                                print("    No data found in this table.")
                    # Error message already printed by get_table_details if details is None
    finally:
        if conn:
            print(f"\nClosing database connection: {db_path}")
            conn.close()

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # This part will only run when the script is executed directly.
    # Create a dummy database for testing
    DB_FILE = "test_db.sqlite"
    conn_test = sqlite3.connect(DB_FILE)
    cursor_test = conn_test.cursor()
    cursor_test.execute("DROP TABLE IF EXISTS users")
    cursor_test.execute("DROP TABLE IF EXISTS products")
    cursor_test.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    cursor_test.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
    cursor_test.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
    cursor_test.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
    cursor_test.execute("INSERT INTO products (name, price) VALUES ('Laptop', 1200.50)")
    cursor_test.execute("INSERT INTO products (name, price) VALUES ('Mouse', 25.99)")
    cursor_test.execute("INSERT INTO products (name, price) VALUES ('Keyboard', 75.00)")
    conn_test.commit()
    conn_test.close()

    print("--- Running display_database_status (summary only) ---")
    display_database_status(db_path=DB_FILE)

    print("\n--- Running display_database_status (with details for all tables) ---")
    display_database_status(db_path=DB_FILE, show_details=True, limit_details=2)

    print("\n--- Running display_database_status (with details for 'users' table) ---")
    display_database_status(db_path=DB_FILE, show_details=True, tables_to_show=['users'], limit_details=3)

    print("\n--- Running display_database_status (with details for non-existent table) ---")
    display_database_status(db_path=DB_FILE, show_details=True, tables_to_show=['non_existent_table'])

    print("\n--- Running display_database_status (for non-existent database) ---")
    display_database_status(db_path="non_existent.db")

    # Clean up the dummy database
    import os
    os.remove(DB_FILE)
    print(f"\nCleaned up {DB_FILE}")
