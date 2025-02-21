import sqlite3

def describe_database(db_path):
    """
    Connects to the SQLite database at db_path and prints a description of its tables, including the number of records.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get a list of all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Describe each table
    print("Database Description:\n")
    for table in tables:
        table_name = table[0]
        print(f"Table: {table_name}")

        # Get the number of records
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"Number of records: {count}")

        # Get column information for each table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()

        # Print column details
        print("Columns:")
        print(f"{'ID':<5} {'Name':<20} {'Type':<15} {'Not Null':<10} {'Default Value':<20}")
        print("-" * 70)
        for column in columns:
            col_id, col_name, col_type, col_notnull, col_default, _ = column
            print(f"{col_id:<5} {col_name:<20} {col_type:<15} {bool(col_notnull):<10} {str(col_default):<20}")
        print("\n")

    # Close the database connection
    conn.close()


describe_database("room_availability.db")