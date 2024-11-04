import json
from collections import defaultdict

def organize_rooms_by_building():
    # Read the room_ids.json file
    try:
        with open("room_ids.json", "r") as f:
            rooms = json.load(f)
    except FileNotFoundError:
        print("Error: room_ids.json not found. Please run get_rooms.py first.")
        return
    
    # Create a defaultdict to store building->rooms mapping
    buildings = defaultdict(list)
    
    # Process each room
    for room in rooms:
        room_name = room["name"]
        # Split room name to get building
        # Assumes format is typically "BUILDING ROOM_NUMBER"
        parts = room_name.split()
        if len(parts) >= 2:
            # Use the first part as building name
            building = parts[0]
            buildings[building].append({
                "id": room["id"],
                "name": room_name,
                "room_number": " ".join(parts[1:])
            })
    
    # Convert defaultdict to regular dict and sort rooms within each building
    organized_buildings = {
        building: sorted(rooms, key=lambda x: x["room_number"]) 
        for building, rooms in buildings.items()
    }
    
    # Save the organized data to a new JSON file
    with open("buildings_organized.json", "w") as f:
        json.dump(organized_buildings, f, indent=2)
    
    # Print summary
    print("\nBuildings and their room counts:")
    for building, rooms in organized_buildings.items():
        print(f"{building}: {len(rooms)} rooms")

if __name__ == "__main__":
    organize_rooms_by_building()
