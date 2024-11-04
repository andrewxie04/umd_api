import sqlite3

def view_database_records(db_path):
    """
    Connects to the SQLite database at db_path and prints some records from the room_availability table.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM room_availability LIMIT 5;")
    records = cursor.fetchall()
    
    # Print column names
    column_names = [description[0] for description in cursor.description]
    print(f"{' | '.join(column_names)}")
    print("-" * 1000)
    
    # Print records
    for record in records:
        print(f"{' | '.join(str(value) for value in record)}")
    
    conn.close()

# Run the function
if __name__ == "__main__":
    view_database_records("room_availability.db")
