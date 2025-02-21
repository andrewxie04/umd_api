import json
import requests
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # Import tqdm for progress bar

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

    def __post_init__(self):
        if self.availability_times is None:
            self.availability_times = []

    def to_dict(self):
        return asdict(self)

@dataclass
class Building:
    """Represents a campus building with classrooms"""
    name: str
    code: str  # Building abbreviation (e.g., 'ESJ')
    building_id: str
    latitude: float
    longitude: float
    classrooms: List[Classroom]

    @classmethod
    def from_api_data(cls, api_data: dict) -> 'Building':
        """Create a Building instance from API response data"""
        return cls(
            name=api_data['name'],
            code=api_data['code'],
            building_id=api_data['id'],
            latitude=float(api_data['lat']),
            longitude=float(api_data['long']),
            classrooms=[]
        )

    def to_dict(self):
        return {
            **asdict(self),
            "classrooms": [classroom.to_dict() for classroom in self.classrooms]
        }

class CampusBuilder:
    """Utility class to build campus building data"""
    BUILDINGS_API_URL = "https://api.umd.io/v1/map/buildings"

    @classmethod
    def fetch_buildings(cls) -> List[Building]:
        """Fetch building data from UMD.io API"""
        try:
            response = requests.get(cls.BUILDINGS_API_URL)
            response.raise_for_status()
            buildings_data = response.json()

            # Create Building objects from API data
            buildings = [Building.from_api_data(b_data) for b_data in buildings_data]
            return buildings

        except requests.RequestException as e:
            print(f"Error fetching building data: {e}")
            return []

    @classmethod
    def load_classrooms_from_json(cls, buildings: List[Building], json_file: str):
        """Load classroom data from JSON file and associate with buildings"""
        try:
            with open(json_file, 'r') as f:
                rooms_data = json.load(f)

            # Create a mapping of building codes to Building objects
            building_map = {b.code: b for b in buildings}

            # Process each room and add to appropriate building
            for room_data in rooms_data:
                # Extract building code from room name (e.g., "ESJ 0202" -> "ESJ")
                room_parts = room_data["name"].split()
                if len(room_parts) >= 2:
                    building_code = room_parts[0]
                    room_number = " ".join(room_parts[1:])

                    if building_code in building_map:
                        classroom = Classroom(
                            id=room_data["id"],
                            name=room_data["name"],
                            room_number=room_number
                        )
                        building_map[building_code].classrooms.append(classroom)

        except FileNotFoundError:
            print(f"Error: Could not find {json_file}")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {json_file}")

def fetch_availability_for_classroom(classroom, start_date=None, page_size=100):
    """
    Fetches room availability data for a specified classroom and updates its availability_times.
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
        "space_id": str(classroom.id),
        "include": "closed blackouts pending related empty",
        "caller": "pro-AvailService.getData"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)  # Added timeout for robustness
        response.raise_for_status()  # Raises HTTPError for bad responses
        data = response.json()

        # Use a dictionary to group events by date, time_start, and time_end
        availability_dict = {}
        for subject in data.get("subjects", []):
            date = subject.get("item_date", "")
            for item in subject.get("items", []):
                time_start = item.get("start", "N/A")
                time_end = item.get("end", "N/A")
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
                    availability_dict[key]["event_name"].append(item.get("itemName", "N/A"))
                    availability_dict[key]["additional_details"].append(item.get("itemId2", "N/A"))
        
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

def fetch_availability_for_all_classrooms(classrooms, start_date=None, max_workers=20):
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
    # Fetch buildings from API
    buildings = CampusBuilder.fetch_buildings()
    print(f"Fetched {len(buildings)} buildings from API")
    
    # Load classrooms from JSON file
    CampusBuilder.load_classrooms_from_json(buildings, "room_ids.json")
    
    # Gather all classrooms
    all_classrooms = [classroom for building in buildings for classroom in building.classrooms]
    print(f"Total classrooms loaded: {len(all_classrooms)}")
    
    # Fetch availability data for all classrooms
    if all_classrooms:
        print(f"Fetching availability data for {len(all_classrooms)} classrooms")
        fetch_availability_for_all_classrooms(all_classrooms)
    else:
        print("No classrooms found to fetch availability data.")
    
    # Filter out buildings with no classrooms
    buildings_with_classrooms = [building for building in buildings if building.classrooms]
    
    # Convert filtered buildings data to dictionary format and export to JSON
    buildings_data = [building.to_dict() for building in buildings_with_classrooms]
    with open("buildings_data.json", "w") as f:
        json.dump(buildings_data, f, indent=4, default=str)
    
    print("Building data with classrooms and availability has been exported to buildings_data.json")

if __name__ == "__main__":
    main()
