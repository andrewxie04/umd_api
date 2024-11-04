import json
import requests
from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class Building:
    """Represents a campus building"""
    name: str
    code: Optional[str]  # Building abbreviation (e.g., 'ESJ'), may be None
    building_id: str
    latitude: float
    longitude: float

    @classmethod
    def from_api_data(cls, api_data: dict) -> 'Building':
        """Create a Building instance from API response data"""
        return cls(
            name=api_data.get('name', ''),
            code=api_data.get('code'),  # May be None
            building_id=api_data.get('id', ''),
            latitude=float(api_data.get('lat', 0)),
            longitude=float(api_data.get('long', 0)),
        )

    def to_dict(self):
        return asdict(self)

def fetch_buildings():
    BUILDINGS_API_URL = "https://api.umd.io/v1/map/buildings"
    try:
        response = requests.get(BUILDINGS_API_URL)
        response.raise_for_status()
        buildings_data = response.json()

        # Create Building objects from API data
        buildings = [Building.from_api_data(b_data) for b_data in buildings_data]
        return buildings

    except requests.RequestException as e:
        print(f"Error fetching building data: {e}")
        return []

def main():
    buildings = fetch_buildings()
    print(f"Fetched {len(buildings)} buildings from API")

    # Save buildings to JSON file
    buildings_data = [building.to_dict() for building in buildings]
    with open("buildings.json", "w") as f:
        json.dump(buildings_data, f, indent=4, default=str)

    print("Building data has been exported to buildings.json")

if __name__ == "__main__":
    main()
