import json
import requests
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import os  # Import os to check for file existence

@dataclass
class Classroom:
    """Represents a classroom within a building"""
    id: int
    name: str
    room_number: str
    capacity: Optional[int] = None
    has_whiteboard: bool = True
    has_projector: bool = True
    availability_times: List[dict] = None
    # Added building info to Classroom
    building_name: Optional[str] = None
    building_code: Optional[str] = None
    building_latitude: Optional[float] = None
    building_longitude: Optional[float] = None

    def __post_init__(self):
        if self.availability_times is None:
            self.availability_times = []

    def to_dict(self):
        return asdict(self)

@dataclass
class Building:
    """Represents a campus building with classrooms"""
    name: str
    code: Optional[str]  # Building abbreviation (e.g., 'ESJ'), may be None
    building_id: str
    latitude: float
    longitude: float
    classrooms: List[Classroom]

    @classmethod
    def from_json(cls, data: dict) -> 'Building':
        """Create a Building instance from JSON data"""
        return cls(
            name=data.get('name', ''),
            code=data.get('code'),
            building_id=data.get('building_id', ''),
            latitude=float(data.get('latitude', 0)),
            longitude=float(data.get('longitude', 0)),
            classrooms=[]
        )

    def to_dict(self):
        return {
            **asdict(self),
            "classrooms": [classroom.to_dict() for classroom in self.classrooms]
        }

def load_buildings(json_file: str) -> List[Building]:
    """Load buildings from JSON file"""
    try:
        with open(json_file, 'r') as f:
            buildings_data = json.load(f)
        buildings = [Building.from_json(b_data) for b_data in buildings_data]
        return buildings
    except FileNotFoundError:
        print(f"Error: Could not find {json_file}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {json_file}")
        return []

def load_classrooms_from_json(buildings: List[Building], json_file: str):
    """Load classroom data from JSON file and associate with buildings"""
    unmatched_classrooms = []
    try:
        with open(json_file, 'r') as f:
            rooms_data = json.load(f)

        # Create mappings of building codes and names to Building objects
        building_map_code = {b.code: b for b in buildings if b.code}
        building_map_name = {b.name: b for b in buildings}

        # Process each room and add to appropriate building
        for room_data in rooms_data:
            # Extract building code from room name (e.g., "ESJ 0202" -> "ESJ")
            room_parts = room_data["name"].split()
            if len(room_parts) >= 2:
                building_code = room_parts[0]
                room_number = " ".join(room_parts[1:])

                if building_code in building_map_code:
                    building = building_map_code[building_code]
                    classroom = Classroom(
                        id=room_data["id"],
                        name=room_data["name"],
                        room_number=room_number,
                        building_name=building.name,
                        building_code=building.code,
                        building_latitude=building.latitude,
                        building_longitude=building.longitude,
                    )
                    building.classrooms.append(classroom)
                else:
                    # Try to use building name
                    building_name = room_parts[0]  # Assuming first part is building name
                    if building_name in building_map_name:
                        building = building_map_name[building_name]
                        classroom = Classroom(
                            id=room_data["id"],
                            name=room_data["name"],
                            room_number=room_number,
                            building_name=building.name,
                            building_code=building.code,
                            building_latitude=building.latitude,
                            building_longitude=building.longitude,
                        )
                        building.classrooms.append(classroom)
                    else:
                        # Could not find building, collect the classroom separately
                        unmatched_classrooms.append(Classroom(
                            id=room_data["id"],
                            name=room_data["name"],
                            room_number=room_number
                        ))
            else:
                # Could not parse room name, collect the classroom separately
                unmatched_classrooms.append(Classroom(
                    id=room_data["id"],
                    name=room_data["name"],
                    room_number=""
                ))
        return unmatched_classrooms

    except FileNotFoundError:
        print(f"Error: Could not find {json_file}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {json_file}")
        return []

def fetch_availability_for_classroom(classroom, start_date=None, page_size=100):
    """
    Fetches room availability data for a specified classroom and updates its availability_times.
    """
    if start_date is None:
        start_date = datetime.today().strftime("%Y-%m-%d")
    
    # Convert start_date to datetime object for comparison
    start_datetime_obj = datetime.strptime(start_date, "%Y-%m-%d")
    start_datetime = f"{start_date}T00:00:00"
    
    url = "https://25live.collegenet.com/25live/data/umd/run/availability/availabilitydata.json"
    params = {
        "obj_cache_accl": "0",
        "start_dt": start_datetime,
        "comptype": "availability_daily",
        "compsubject": "location",
        "page_size": str(page_size),
        "space_id": str(classroom.id),
        "include": "closed blackouts pending related empty",
        "caller": "pro-AvailService.getData"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Use a dictionary to group events by date, time_start, and time_end
        availability_dict = {}
        for subject in data.get("subjects", []):
            date = subject.get("item_date", "")
            # Skip if date is empty or invalid
            if not date:
                continue
            
            # Convert date string to datetime object for comparison
            try:
                event_date = datetime.strptime(date, "%Y-%m-%d")
                # Skip events from before the start date
                if event_date < start_datetime_obj:
                    continue
            except ValueError:
                continue

            for item in subject.get("items", []):
                time_start = item.get("start", "N/A")
                time_end = item.get("end", "N/A")
                # Skip invalid time entries
                if time_start == "N/A" or time_end == "N/A":
                    continue

                key = (date, time_start, time_end)
                if key not in availability_dict:
                    availability_dict[key] = {
                        "date": date,
                        "event_name": [item.get("itemName", "N/A")],
                        "time_start": time_start,
                        "time_end": time_end,
                        "status": item.get("type_id", "N/A"),
                        "additional_details": [item.get("itemId2", "N/A")]
                    }
                else:
                    # Only append if it's not already in the list
                    event_name = item.get("itemName", "N/A")
                    if event_name not in availability_dict[key]["event_name"]:
                        availability_dict[key]["event_name"].append(event_name)
                    
                    item_id = item.get("itemId2", "N/A")
                    if item_id not in availability_dict[key]["additional_details"]:
                        availability_dict[key]["additional_details"].append(item_id)

        # Convert the grouped data back into a list and combine event names
        availability = []
        for entry in availability_dict.values():
            entry["event_name"] = ', '.join(entry["event_name"])
            entry["additional_details"] = ', '.join(map(str, entry["additional_details"]))
            availability.append(entry)
        
        classroom.availability_times = availability

    except requests.exceptions.RequestException as e:
        print(f"Request error for classroom {classroom.id}: {e}")
        classroom.availability_times = []
    except json.JSONDecodeError:
        print(f"JSON decode error for classroom {classroom.id}")
        classroom.availability_times = []
    except Exception as e:
        print(f"Unexpected error for classroom {classroom.id}: {e}")
        classroom.availability_times = []

def fetch_availability_for_all_classrooms(classrooms, start_date=None, max_workers=50):
    """
    Fetches availability data for multiple classrooms using multithreading.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_classroom = {
            executor.submit(fetch_availability_for_classroom, classroom, start_date): classroom
            for classroom in classrooms
        }
        for future in tqdm(as_completed(future_to_classroom), total=len(future_to_classroom), desc="Fetching classroom availability"):
            classroom = future_to_classroom[future]
            try:
                future.result()
            except Exception as e:
                print(f"Error fetching data for classroom {classroom.id}: {e}")

def main():
    # Load buildings from JSON file
    buildings = load_buildings("buildings.json")
    print(f"Loaded {len(buildings)} buildings from buildings.json")
    
    # Load classrooms from JSON file and associate with buildings
    unmatched_classrooms = load_classrooms_from_json(buildings, "room_ids.json")
    
    # Gather all classrooms
    all_classrooms = [classroom for building in buildings for classroom in building.classrooms]
    total_classrooms = len(all_classrooms) + len(unmatched_classrooms)
    print(f"Total classrooms loaded: {total_classrooms}")
    
    # Fetch availability data for all classrooms
    if total_classrooms:
        print(f"Fetching availability data for {total_classrooms} classrooms")
        # Fetch availability for classrooms associated with buildings
        fetch_availability_for_all_classrooms(all_classrooms + unmatched_classrooms)
    else:
        print("No classrooms found to fetch availability data.")
    
    # Define the file to store labeled unmatched classrooms
    labeled_classrooms_file = "labeled_unmatched_classrooms.json"
    
    if os.path.exists(labeled_classrooms_file):
        # Load previously labeled unmatched classrooms
        try:
            with open(labeled_classrooms_file, "r") as f:
                labeled_unmatched_classrooms_data = json.load(f)
            labeled_unmatched_classrooms = []
            for data in labeled_unmatched_classrooms_data:
                # Check if all required building information is present
                if all([
                    data.get('building_name'),
                    data.get('building_code'),
                    data.get('building_latitude') is not None,
                    data.get('building_longitude') is not None
                ]):
                    classroom = Classroom(
                        id=data['id'],
                        name=data['name'],
                        room_number=data['room_number'],
                        building_name=data.get('building_name'),
                        building_code=data.get('building_code'),
                        building_latitude=float(data.get('building_latitude', 0)),
                        building_longitude=float(data.get('building_longitude', 0)),
                        availability_times=data.get('availability_times', []),
                        capacity=data.get('capacity'),
                        has_whiteboard=data.get('has_whiteboard', True),
                        has_projector=data.get('has_projector', True)
                    )
                    labeled_unmatched_classrooms.append(classroom)
                else:
                    print(f"Skipping classroom {data.get('id')} due to incomplete labeling.")
            
            # Group classrooms by building code or name
            for classroom in labeled_unmatched_classrooms:
                # Try to find existing building
                building = None
                if classroom.building_code:
                    building = next((b for b in buildings if b.code == classroom.building_code), None)
                if not building and classroom.building_name:
                    building = next((b for b in buildings if b.name == classroom.building_name), None)
                if not building:
                    # Create new building
                    building = Building(
                        name=classroom.building_name or "Unknown",
                        code=classroom.building_code,
                        building_id="",  # Building ID can be left empty or set as needed
                        latitude=classroom.building_latitude or 0,
                        longitude=classroom.building_longitude or 0,
                        classrooms=[]
                    )
                    buildings.append(building)
                building.classrooms.append(classroom)
        except Exception as e:
            print(f"Error reading labeled unmatched classrooms: {e}")
    else:
        # If no labeled classrooms file, create one for labeling
        unmatched_classrooms_data = [classroom.to_dict() for classroom in unmatched_classrooms]
        if unmatched_classrooms_data:
            # Create a file for the user to label unmatched classrooms
            with open("unmatched_classrooms_to_label.json", "w") as f:
                json.dump(unmatched_classrooms_data, f, indent=4, default=str)
            print("Unmatched classrooms have been exported to unmatched_classrooms_to_label.json for labeling.")
            
            # Prompt the user to label the unmatched classrooms
            print("Please label the unmatched classrooms in 'unmatched_classrooms_to_label.json' by adding building information.")
            input("Press Enter after labeling the unmatched classrooms...")
            
            # Read the labeled unmatched classrooms
            try:
                with open("unmatched_classrooms_to_label.json", "r") as f:
                    labeled_unmatched_classrooms_data = json.load(f)
                labeled_unmatched_classrooms = []
                discarded_classrooms = []
                for data in labeled_unmatched_classrooms_data:
                    # Check if all required building information is present
                    if all([
                        data.get('building_name'),
                        data.get('building_code'),
                        data.get('building_latitude') is not None,
                        data.get('building_longitude') is not None
                    ]):
                        classroom = Classroom(
                            id=data['id'],
                            name=data['name'],
                            room_number=data['room_number'],
                            building_name=data.get('building_name'),
                            building_code=data.get('building_code'),
                            building_latitude=float(data.get('building_latitude', 0)),
                            building_longitude=float(data.get('building_longitude', 0)),
                            availability_times=data.get('availability_times', []),
                            capacity=data.get('capacity'),
                            has_whiteboard=data.get('has_whiteboard', True),
                            has_projector=data.get('has_projector', True)
                        )
                        labeled_unmatched_classrooms.append(classroom)
                    else:
                        # If labeling is incomplete, discard the classroom
                        discarded_classrooms.append(data['id'])
                        print(f"Discarding classroom {data.get('id')} due to incomplete labeling.")
                
                # Save labeled unmatched classrooms for future runs
                with open(labeled_classrooms_file, "w") as f:
                    json.dump([c.to_dict() for c in labeled_unmatched_classrooms], f, indent=4, default=str)
                
                # Group classrooms by building code or name
                for classroom in labeled_unmatched_classrooms:
                    # Try to find existing building
                    building = None
                    if classroom.building_code:
                        building = next((b for b in buildings if b.code == classroom.building_code), None)
                    if not building and classroom.building_name:
                        building = next((b for b in buildings if b.name == classroom.building_name), None)
                    if not building:
                        # Create new building
                        building = Building(
                            name=classroom.building_name or "Unknown",
                            code=classroom.building_code,
                            building_id="",  # Building ID can be left empty or set as needed
                            latitude=classroom.building_latitude or 0,
                            longitude=classroom.building_longitude or 0,
                            classrooms=[]
                        )
                        buildings.append(building)
                    building.classrooms.append(classroom)
                
                # Optionally, remove the processed unmatched classrooms file
                os.remove("unmatched_classrooms_to_label.json")
                
                # Notify about discarded classrooms
                if discarded_classrooms:
                    print(f"Discarded {len(discarded_classrooms)} classrooms due to incomplete labeling.")
            except Exception as e:
                print(f"Error reading labeled unmatched classrooms: {e}")
        else:
            print("No unmatched classrooms with availability found.")
    
    # Filter out buildings with no classrooms
    buildings_with_classrooms = [building for building in buildings if building.classrooms]
    
    # Convert buildings data to dictionary format and export to JSON
    buildings_data = [building.to_dict() for building in buildings_with_classrooms]
    with open("buildings_data.json", "w") as f:
        json.dump(buildings_data, f, indent=4, default=str)
    
    print("Building data with classrooms and availability has been exported to buildings_data.json")

if __name__ == "__main__":
    main()
