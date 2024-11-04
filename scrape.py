import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import json
from tqdm import tqdm  # Import tqdm for progress bar

def fetch_single_room_availability(space_id, start_date=None, page_size=100):
    """
    Fetches room availability data for a specified room (space_id) and start date.

    Parameters:
        space_id (int): Unique ID of the room.
        start_date (str): Start date in YYYY-MM-DD format. Defaults to today's date if None.
        page_size (int): Number of entries per page. Default is 100.

    Returns:
        list of dict: Availability data for the room.
    """
    if start_date is None:
        start_date = datetime.today().strftime("%Y-%m-%d")
        
    start_datetime = f"{start_date}T00:00:00"
    
    url = "https://25live.collegenet.com/25live/data/umd/run/availability/availabilitydata.json"
    params = {
        "obj_cache_accl": "0",
        "start_dt": start_datetime,
        "comptype": "availability_daily",
        "compsubject": "location",
        "page_size": str(page_size),
        "space_id": str(space_id),
        "include": "closed blackouts pending related empty",
        "caller": "pro-AvailService.getData"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)  # Added timeout for robustness
        response.raise_for_status()  # Raises HTTPError for bad responses
        data = response.json()
        availability = []
        for subject in data.get("subjects", []):
            date = subject.get("item_date", "")
            for item in subject.get("items", []):
                availability.append({
                    "room_id": space_id,
                    "date": date,
                    "event_name": item.get("itemName", "N/A"),
                    "time_start": item.get("start", "N/A"),
                    "time_end": item.get("end", "N/A"),
                    "status": item.get("type_id", "N/A"),  
                    "additional_details": item.get("itemId2", "N/A")
                })
        return availability
    except requests.exceptions.RequestException as e:
        print(f"Request error for room {space_id}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"JSON decode error for room {space_id}")
        return []
    except Exception as e:
        print(f"Unexpected error for room {space_id}: {e}")
        return []

def fetch_all_rooms_availability(room_ids, start_date=None, max_workers=40):
    """
    Fetches room availability data for multiple rooms using multithreading.

    Parameters:
        room_ids (list of dict): List of room dictionaries with 'id' and 'name' keys.
        start_date (str): Start date in YYYY-MM-DD format. Defaults to today's date if None.
        max_workers (int): Maximum number of threads to use. Default is 20.

    Returns:
        None
    """
    all_availability = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and map futures to room IDs
        future_to_room = {
            executor.submit(fetch_single_room_availability, room['id'], start_date): room
            for room in room_ids
        }
        
        # Initialize tqdm progress bar
        for future in tqdm(as_completed(future_to_room), total=len(future_to_room), desc="Fetching room availability"):
            room = future_to_room[future]
            try:
                result = future.result()
                if result:
                    all_availability.extend(result)
            except Exception as e:
                print(f"Error fetching data for room {room['id']}: {e}")
    
    # Store the collected data into the SQLite database
    store_availability_to_db(all_availability)


def store_availability_to_db(availability_data):
    """
    Stores room availability data into an SQLite database.

    Parameters:
        availability_data (list of dict): Room availability data.

    Returns:
        None
    """
    if not availability_data:
        print("No availability data to store.")
        return

    conn = sqlite3.connect("room_availability.db")
    cursor = conn.cursor()
    
    # Drop table if it exists to ensure schema matches
    cursor.execute("DROP TABLE IF EXISTS room_availability")

    # Create table with the correct schema
    cursor.execute("""
        CREATE TABLE room_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            date TEXT,
            event_name TEXT,
            time_start REAL,
            time_end REAL,
            status INTEGER,
            additional_details TEXT
        )
    """)

    # Prepare data for insertion
    records = []
    for item in availability_data:
        try:
            # Convert time_start and time_end to float, handle "N/A"
            time_start = float(item["time_start"]) if item["time_start"] != "N/A" else None
            time_end = float(item["time_end"]) if item["time_end"] != "N/A" else None
            # Convert status to integer, handle "N/A"
            status = int(item["status"]) if item["status"] != "N/A" else None
            record = (
                item["room_id"], 
                item["date"], 
                item["event_name"], 
                time_start, 
                time_end, 
                status, 
                item["additional_details"]
            )
            records.append(record)
        except (KeyError, ValueError) as e:
            print(f"Error processing item {item}: {e}")

    if not records:
        print("No records to insert.")
        return

    try:
        # Insert data
        cursor.executemany("""
            INSERT INTO room_availability (room_id, date, event_name, time_start, time_end, status, additional_details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, records)
        
        conn.commit()
        print(f"Inserted {len(records)} records into the database.")
    except Exception as e:
        print(f"Error inserting records into the database: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # Load room IDs from JSON file
    try:
        with open("room_ids.json", "r") as file:
            room_ids = json.load(file)
    except FileNotFoundError:
        print("The file 'room_ids.json' was not found.")
        room_ids = []
    except json.JSONDecodeError:
        print("Error decoding 'room_ids.json'. Ensure it is valid JSON.")
        room_ids = []
    
    if room_ids:
        # Fetch availability for all rooms and store in the database
        fetch_all_rooms_availability(room_ids)
    else:
        print("No room IDs to process.")
