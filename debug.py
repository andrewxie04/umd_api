import requests
import pandas as pd
from datetime import datetime

def fetch_single_room_availability(space_id, start_date=None, page_size=100):
    """
    Fetches room availability data for a specified room (space_id) and start date.

    Parameters:
        space_id (int): Unique ID of the room.
        start_date (str): Start date in YYYY-MM-DD format. Defaults to today's date if None.
        page_size (int): Number of entries per page. Default is 100.

    Returns:
        None
    """
    # Use today's date if no start date is provided
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
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print("Raw JSON Response:")
        print(data)

        availability = []
        for subject in data.get("subjects", []):
            date = subject.get("item_date", "")
            for item in subject.get("items", []):
                availability.append({
                    "Room ID": space_id,
                    "Date": date,
                    "Event Name": item.get("itemName", "N/A"),
                    "Time Start": item.get("start", "N/A"),
                    "Time End": item.get("end", "N/A"),
                    "Status": item.get("type_id", "N/A"),  # Possible status or type field
                    "Additional Details": item.get("itemId2", "N/A")
                })

        df = pd.DataFrame(availability)
        df.to_csv(f"single_room_{space_id}_availability.csv", index=False)
        print(f"Saved availability data to 'single_room_{space_id}_availability.csv'")
        print(df.head())
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")

# Test the function with a single room ID
fetch_single_room_availability(space_id=2984)
