import requests
import json

def fetch_all_room_ids():
    # API endpoint to get all rooms
    url = "https://25live.collegenet.com/25live/data/umd/run/list/listdata.json"
    params = {
        "compsubject": "location",
        "sort": "name",
        "order": "asc",
        "page": "1",
        "page_size": "380",  # Set to 380 to retrieve all entries in one call
        "obj_cache_accl": "0",
        "category_id": "2 8 7 43 5 12 100 14 82 83 84",
        "caller": "pro-ListService.getData"
    }

    # Send the request to the API
    response = requests.get(url, params=params)
    
    # Check if the response is successful
    if response.status_code == 200:
        data = response.json()  # Parse JSON data
        print("Raw JSON Response:")
        print(data)  # Uncomment to inspect the structure if needed

        # Extract room IDs
        room_ids = []
        for row_entry in data.get("rows", []):
            for room in row_entry.get("row", []):
                if isinstance(room, dict):  # Check if 'room' is a dictionary
                    room_id = room.get("itemId")
                    room_name = room.get("itemName")
                    if room_id:
                        room_ids.append({"id": room_id, "name": room_name})
        
        # Save room IDs to a JSON file
        with open("room_ids.json", "w") as f:
            json.dump(room_ids, f)
        
        print(f"Saved {len(room_ids)} room IDs to 'room_ids.json'")
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")

# Run the function
fetch_all_room_ids()
