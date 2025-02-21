import requests
import json
from datetime import datetime
from collections import defaultdict

# URL of the availability grid
url = 'https://umd.libcal.com/spaces/availability/grid'

# Headers extracted from the curl command
headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://umd.libcal.com',
    'Pragma': 'no-cache',
    'Referer': 'https://umd.libcal.com/spaces?lid=2552&gid=23067&c=0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 '
                  'Safari/537.36 Edg/130.0.0.0',
    'X-Requested-With': 'XMLHttpRequest',
}

# Data extracted from the curl command
payload = {
    'lid': '2552',
    'gid': '23067',
    'eid': '-1',
    'seat': '0',
    'seatId': '0',
    'zone': '0',
    'start': '2024-11-14',
    'end': '2024-11-15',
    'pageIndex': '0',
    'pageSize': '18',
}

# Optional: Mapping of itemId to space names
# Replace the following dictionary with actual mappings if available
ITEM_ID_TO_NAME = {
    86403: 'Study Room 201',
    # Add more mappings as needed
}

def fetch_availability_data():
    """
    Sends a POST request to the URL with the specified headers and payload.
    Returns the JSON response.
    """
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()  # Check for HTTP errors
        print("Data fetched successfully.\n")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data: {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON response.")
        return None

def parse_datetime(dt_str):
    """
    Parses a datetime string and returns a formatted string.
    """
    try:
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %I:%M %p')
    except ValueError:
        return dt_str  # Return as-is if format is unexpected

def analyze_data(data):
    """
    Analyzes the JSON data to extract and display availability information.
    """
    if not isinstance(data, dict):
        print("Unexpected data format: Root element is not a dictionary.")
        return

    # Extract relevant keys
    slots = data.get('slots', [])
    bookings = data.get('bookings', [])
    is_pre_created_booking = data.get('isPreCreatedBooking', False)
    window_end = data.get('windowEnd', False)

    if not slots:
        print("No availability slots found in the response.")
        return

    # Organize slots by itemId
    availability_dict = defaultdict(list)
    for slot in slots:
        item_id = slot.get('itemId', 'Unknown ID')
        availability_dict[item_id].append(slot)

    print("--- Availability Summary ---\n")

    for item_id, events in availability_dict.items():
        space_name = ITEM_ID_TO_NAME.get(item_id, f"Unknown Space (ID: {item_id})")
        print(f"Space: {space_name}")
        # To avoid excessive output, we'll summarize bookings
        total_slots = len(events)
        booked_slots = [e for e in events if e.get('className') == 's-lc-eq-checkout']
        available_slots = total_slots - len(booked_slots)

        print(f"  Total Slots: {total_slots}")
        print(f"  Booked Slots: {len(booked_slots)}")
        print(f"  Available Slots: {available_slots}\n")

        # Optionally, display first few booked and available slots
        preview_count = 3

        if booked_slots:
            print(f"  Booked Slots Preview:")
            for slot in booked_slots[:preview_count]:
                start = parse_datetime(slot.get('start', 'N/A'))
                end = parse_datetime(slot.get('end', 'N/A'))
                print(f"    {start} - {end}")
            if len(booked_slots) > preview_count:
                print(f"    ...and {len(booked_slots) - preview_count} more booked slots.\n")
        else:
            print("  No Booked Slots.\n")

        if available_slots > 0:
            available_list = [e for e in events if e.get('className') != 's-lc-eq-checkout']
            print(f"  Available Slots Preview:")
            for slot in available_list[:preview_count]:
                start = parse_datetime(slot.get('start', 'N/A'))
                end = parse_datetime(slot.get('end', 'N/A'))
                print(f"    {start} - {end}")
            if len(available_list) > preview_count:
                print(f"    ...and {len(available_list) - preview_count} more available slots.\n")
        else:
            print("  No Available Slots.\n")

    # Display additional information
    print("--- Additional Information ---")
    print(f"Is Pre-Created Booking: {is_pre_created_booking}")
    print(f"Window End: {window_end}")
    print("--- End of Summary ---\n")

def main():
    data = fetch_availability_data()
    if data:
        analyze_data(data)
    else:
        print("No data to analyze.")

if __name__ == '__main__':
    main()
