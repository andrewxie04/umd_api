import json

def analyze_json(data, level=0):
    """
    Recursively analyze the JSON structure and print details about each key and data type.
    
    Parameters:
        data (dict or list): JSON data to analyze.
        level (int): Current level of nesting for pretty-printing.
    """
    indent = "  " * level  # indentation for pretty-printing
    
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{indent}Key: '{key}' - Type: {type(value).__name__}")
            analyze_json(value, level + 1)
    elif isinstance(data, list):
        print(f"{indent}List of {len(data)} items - Type of items: {type(data[0]).__name__ if data else 'Unknown'}")
        for item in data[:1]:  # analyze only the first item for simplicity
            analyze_json(item, level + 1)
    else:
        print(f"{indent}Value: '{data}' - Type: {type(data).__name__}")

def main():
    # Load JSON data from 'buildings_data.json'
    try:
        with open('buildings_data.json', 'r') as file:
            data = json.load(file)
        
        print("JSON Structure and Layout Analysis:\n")
        analyze_json(data)
    
    except FileNotFoundError:
        print("The file 'buildins_info.json' was not found.")
    except json.JSONDecodeError:
        print("The file 'buildins_info.json' is not a valid JSON file.")

if __name__ == "__main__":
    main()
