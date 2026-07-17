#!/usr/bin/env python3
import json
import os
import sys

def extract_game_ids(repo_path, game_ids_path):
    """
    Extract game ID fields from port.json files and merge with an existing game_ids.json file.
    
    Args:
        repo_path: Path to the repository containing ports
        game_ids_path: Path to the existing game_ids.json file
    """
    ports_dir = os.path.join(repo_path, "ports")
    
    # Define the fields we want to extract
    id_fields = ["igdb_id", "steam_id", "itchio_url"]
    
    # Load existing game IDs if file exists
    existing_game_ids = {}
    if os.path.exists(game_ids_path):
        try:
            with open(game_ids_path, 'r') as f:
                existing_game_ids = json.load(f)
            print(f"Loaded {len(existing_game_ids)} existing game IDs from {game_ids_path}")
        except json.JSONDecodeError:
            print(f"Error parsing existing {game_ids_path}, starting with empty dictionary")
    
    # Initialize the new game IDs dictionary
    new_game_ids = {}
    
    # Count statistics
    stats = {field: 0 for field in id_fields}
    total_ports = 0
    ports_with_ids = 0
    new_entries = 0
    updated_entries = 0
    
    # Walk through all port directories
    for port_name in os.listdir(ports_dir):
        port_dir = os.path.join(ports_dir, port_name)
        
        # Skip if not a directory
        if not os.path.isdir(port_dir):
            continue
            
        port_json_path = os.path.join(port_dir, "port.json")
        
        # Skip if port.json doesn't exist
        if not os.path.exists(port_json_path):
            continue
            
        total_ports += 1
        
        # Read the port.json file
        try:
            with open(port_json_path, 'r') as f:
                port_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error parsing {port_json_path}")
            continue
        
        # Extract ID fields
        port_ids = {}
        for field in id_fields:
            if field in port_data.get('attr', {}):
                port_ids[field] = port_data['attr'][field]
                stats[field] += 1
        
        # Store IDs if any field was found
        if port_ids:
            new_game_ids[port_name] = port_ids
            ports_with_ids += 1
    
    # Merge with existing game IDs
    merged_game_ids = existing_game_ids.copy()
    for port_name, port_ids in new_game_ids.items():
        if port_name not in merged_game_ids:
            merged_game_ids[port_name] = port_ids
            new_entries += 1
        else:
            # Update existing entry with any new fields
            for field, value in port_ids.items():
                if field not in merged_game_ids[port_name] or merged_game_ids[port_name][field] != value:
                    merged_game_ids[port_name][field] = value
                    updated_entries += 1
    
    # Write merged game IDs to file
    with open(game_ids_path, 'w') as f:
        json.dump(merged_game_ids, f, indent=2)
    
    # Print statistics
    print(f"Total ports processed: {total_ports}")
    print(f"Ports with game IDs: {ports_with_ids}")
    for field in id_fields:
        print(f"{field}: {stats[field]} ports")
    print(f"New entries added: {new_entries}")
    print(f"Existing entries updated: {updated_entries}")
    print(f"Total entries in output file: {len(merged_game_ids)}")
    print(f"Game IDs saved to {game_ids_path}")

def remove_ids_from_ports(repo_path):
    """
    Remove ID fields from port.json files after extracting them.
    
    Args:
        repo_path: Path to the repository containing ports
    """
    ports_dir = os.path.join(repo_path, "ports")
    
    # Define the fields we want to remove
    id_fields = ["igdb_id", "steam_id", "itchio_url", "igdb_visits"]  # Include igdb_visits for removal
    
    # Count modified files
    modified_files = 0
    
    # Walk through all port directories
    for port_name in os.listdir(ports_dir):
        port_dir = os.path.join(ports_dir, port_name)
        
        # Skip if not a directory
        if not os.path.isdir(port_dir):
            continue
            
        port_json_path = os.path.join(port_dir, "port.json")
        
        # Skip if port.json doesn't exist
        if not os.path.exists(port_json_path):
            continue
        
        # Read the port.json file
        try:
            with open(port_json_path, 'r') as f:
                port_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error parsing {port_json_path}")
            continue
        
        # Check if any field needs to be removed
        modified = False
        for field in id_fields:
            if field in port_data.get('attr', {}):
                del port_data['attr'][field]
                modified = True
        
        # Write back the modified port.json if needed
        if modified:
            # Create a backup
            backup_path = f"{port_json_path}.bak"
            os.rename(port_json_path, backup_path)
            
            # Write updated data
            with open(port_json_path, 'w') as f:
                json.dump(port_data, f, indent=4)
            
            modified_files += 1
    
    print(f"Modified {modified_files} port.json files")

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_game_ids.py <repo_path> <game_ids.json> [--remove]")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    game_ids_path = sys.argv[2]
    remove_flag = len(sys.argv) > 3 and sys.argv[3] == "--remove"
    
    # Extract game IDs
    extract_game_ids(repo_path, game_ids_path)
    
    # Optionally remove ID fields from port.json files
    if remove_flag:
        print("Removing ID fields from port.json files...")
        remove_ids_from_ports(repo_path)

if __name__ == "__main__":
    main()
