import json
import requests
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime, time

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
    
    def add_availability(self, start_time: time, end_time: time, day_of_week: str):
        """Add an availability time slot"""
        self.availability_times.append({
            'start_time': start_time,
            'end_time': end_time,
            'day_of_week': day_of_week
        })

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

def main():
    # Fetch buildings from API
    buildings = CampusBuilder.fetch_buildings()
    print(f"Fetched {len(buildings)} buildings from API")
    
    # Load classrooms from JSON file
    CampusBuilder.load_classrooms_from_json(buildings, "room_ids.json")
    
    # Filter out buildings with no classrooms
    buildings_with_classrooms = [building for building in buildings if building.classrooms]
    
    # Convert filtered buildings data to dictionary format and export to JSON
    buildings_data = [building.to_dict() for building in buildings_with_classrooms]
    with open("buildings_data.json", "w") as f:
        json.dump(buildings_data, f, indent=4, default=str)
    
    print("Building data with classrooms has been exported to buildings_data.json")

if __name__ == "__main__":
    main()
