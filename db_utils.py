import sqlite3
import pandas as pd

def connect_db(db_path: str) -> sqlite3.Connection | None:
    """
    Establishes a connection to the SQLite database specified by db_path.

    Args:
        db_path (str): The absolute path to the SQLite database file.
                       If the database does not exist, it will be created.

    Returns:
        sqlite3.Connection: A connection object to the SQLite database if successful.
        None: If an error occurs during connection (e.g., database file is corrupted,
              permissions issues).
    """
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_path}: {e}")
        return None

def get_db_summary(conn: sqlite3.Connection) -> str:
    """
    Generates a summary of the SQLite database, listing all tables and their respective row counts.

    Args:
        conn (sqlite3.Connection): The active connection object to the SQLite database.

    Returns:
        str: A multi-line string providing a human-readable summary of the database.
             Includes table names and their row counts. Returns an appropriate message
             if there's no connection, no tables, or an error during query.
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

def get_table_details(conn: sqlite3.Connection, table_name: str, limit: int = 5) -> pd.DataFrame | tuple[list[tuple], list[str]] | None:
    """
    Fetches a limited number of rows and column details from a specified SQLite table.

    Args:
        conn (sqlite3.Connection): The active connection object to the SQLite database.
        table_name (str): The name of the table from which to fetch details.
        limit (int, optional): The maximum number of rows to retrieve from the table.
                               Defaults to 5.

    Returns:
        pandas.DataFrame: If pandas is installed, returns a DataFrame containing the
                          fetched rows and column names.
        tuple[list[tuple], list[str]]: If pandas is not installed, returns a tuple where
                                       the first element is a list of tuples (rows) and
                                       the second is a list of column names.
        None: If the database connection is invalid or an error occurs during the query.
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

def display_database_status(db_path: str = "data.db", show_details: bool = False, tables_to_show: list[str] | None = None, limit_details: int = 5) -> None:
    """
    Displays the status of an SQLite database, including a summary of tables and
    optionally detailed content for specific tables.

    Args:
        db_path (str, optional): The path to the SQLite database file. Defaults to "data.db".
        show_details (bool, optional): If True, detailed content (rows) of tables will be displayed.
                                       Defaults to False.
        tables_to_show (list[str] | None, optional): A list of table names for which to display details.
                                                     If None and `show_details` is True, details for all
                                                     tables in the database will be shown. Defaults to None.
        limit_details (int, optional): The maximum number of rows to display for each table's details
                                       when `show_details` is True. Defaults to 5.
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
