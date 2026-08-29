#!/usr/bin/env python3
"""
Script to generate popularity metrics for PortMaster games from IGDB.
Takes a specified game_ids.json file as input, fetches popularity metrics,
and outputs them to the specified output file.

Usage: 
    python3 igdb_popularity.py /path/to/game_ids.json [/path/to/output.json]
    
If output path is not specified, it will save to 'popularity.json' in the same directory
as the script.
"""

import os
import sys
import json
import requests
import time
import argparse

# === Configuration ===
CLIENT_ID = 'ljcuthcgsxztbyax36whgzdst5s68u'
CLIENT_SECRET = 'l6fzl17soljtxhsswavk7kbps5s876'

# === Parse Arguments ===
def parse_arguments():
    parser = argparse.ArgumentParser(description='Fetch IGDB popularity metrics for games')
    parser.add_argument('game_ids_file', help='Path to game_ids.json file')
    parser.add_argument('output_file', nargs='?', help='Path to output popularity.json file')
    return parser.parse_args()

# === Authorization & Setup ===
def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Missing CLIENT_ID or CLIENT_SECRET.", file=sys.stderr)
        sys.exit(1)
        
    try:
        resp = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "client_credentials"
            },
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except requests.RequestException as e:
        print(f"Failed to get token: {e}", file=sys.stderr)
        sys.exit(1)

# === Robust request with retries ===
def retry_request(method, url, **kwargs):
    for attempt in range(5):
        try:
            resp = requests.request(method, url, timeout=15, **kwargs)
            print(f"Got status code {resp.status_code}", file=sys.stderr)
            if resp.status_code == 400 and attempt < 4:
                print("Warning: 400 error – retrying...", file=sys.stderr)
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    print(f"Failed after 5 attempts: {url}", file=sys.stderr)
    return None

# === Extract IGDB IDs from game_ids.json file ===
def extract_igdb_ids(game_ids_file):
    igdb_mapping = {}  # Maps IGDB IDs to game keys (port directory names)
    game_count = 0
    
    print(f"Reading IGDB IDs from {game_ids_file}...")
    
    try:
        with open(game_ids_file, 'r') as f:
            game_ids_json = json.load(f)
        
        for game_key, game_data in game_ids_json.items():
            game_count += 1
            # Extract igdb_id if present
            if 'igdb_id' in game_data and game_data['igdb_id']:
                igdb_id = str(game_data['igdb_id'])
                igdb_mapping[igdb_id] = game_key
                print(f"Found IGDB ID {igdb_id} for game {game_key}")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error processing {game_ids_file}: {e}")
        sys.exit(1)
    
    print(f"Found {len(igdb_mapping)} IGDB IDs out of {game_count} games")
    return igdb_mapping

# === Fetch popularity data for all IDs ===
def fetch_popularity_data(igdb_mapping, headers):
    metrics_by_game = {}
    type_ids = set()
    
    print(f"Fetching popularity data for {len(igdb_mapping)} games...")
    
    for i, (gid, game_key) in enumerate(igdb_mapping.items()):
        print(f"Processing game {i+1}/{len(igdb_mapping)}: {game_key} (ID {gid})")
        
        # Respect rate limits
        time.sleep(1.0)  # IGDB rate limit: max 4 req/sec
        
        query = (
            "fields calculated_at,checksum,created_at,external_popularity_source,game_id,"
            "popularity_source,popularity_type,updated_at,value;"
            f"where game_id = {gid};"
        )
        resp = retry_request("POST", "https://api.igdb.com/v4/popularity_primitives", headers=headers, data=query)
        if not resp:
            continue

        primitives = resp.json()
        if not primitives:
            print(f"No popularity data for game {game_key} (ID {gid})")
            continue

        metrics_by_game[game_key] = {}
        for p in primitives:
            tid = str(p["popularity_type"])
            metrics_by_game[game_key][tid] = p["value"]
            type_ids.add(p["popularity_type"])
    
    return metrics_by_game, type_ids

# === Fetch popularity type names ===
def fetch_popularity_types(headers):
    print("Fetching popularity type information...")
    
    types_dict = {}
    type_query = "fields name,popularity_source,updated_at; sort id asc;"
    
    resp = retry_request("POST", "https://api.igdb.com/v4/popularity_types", headers=headers, data=type_query)
    if resp:
        types = resp.json()
        types_dict = {str(t["id"]): t["name"] for t in types}
    
    return types_dict

# === Main function ===
def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Set default output file if not specified
    if not args.output_file:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "popularity.json")
    else:
        output_file = args.output_file
    
    # Get authentication token
    ACCESS_TOKEN = get_access_token()
    HEADERS = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    # Extract IDs from game_ids.json file and map them to game keys
    igdb_mapping = extract_igdb_ids(args.game_ids_file)
    if not igdb_mapping:
        print("No valid IGDB IDs found in the game_ids.json file.", file=sys.stderr)
        sys.exit(1)
    
    # Get existing popularity data if available
    existing_data = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_data = json.load(f)
                print(f"Loaded existing popularity data with {len(existing_data.get('popularity_metrics', {}))} entries")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading existing popularity data: {e}")
    
    # Fetch metrics for games
    metrics_by_game, type_ids = fetch_popularity_data(igdb_mapping, HEADERS)
    
    # Fetch popularity type names
    types_dict = fetch_popularity_types(HEADERS)
    
    # Merge with existing data if available
    if existing_data:
        # Create a reverse mapping (IGDB ID -> game key) for existing data
        existing_metrics = existing_data.get('popularity_metrics', {})
        
        # First, try to convert any numeric keys in existing data to game keys
        # Create a copy to avoid modifying while iterating
        existing_keys = list(existing_metrics.keys())
        for key in existing_keys:
            # If the key is numeric (an IGDB ID), try to map it to a game key
            if key.isdigit():
                # If we have this ID in our current mapping
                if key in igdb_mapping:
                    game_key = igdb_mapping[key]
                    # If this game key doesn't already exist in metrics
                    if game_key not in existing_metrics:
                        existing_metrics[game_key] = existing_metrics[key]
                    # Remove the numeric key entry
                    del existing_metrics[key]
        
        # Now merge the new metrics into the existing ones
        for game_key, metrics in metrics_by_game.items():
            existing_metrics[game_key] = metrics
        
        metrics_by_game = existing_metrics
        
        # Merge types
        existing_types = existing_data.get('popularity_types', {})
        types_dict.update(existing_types)
    
    # Prepare output
    output = {
        "popularity_types": types_dict,
        "popularity_metrics": metrics_by_game
    }
    
    # Write to file
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, sort_keys=True)
    
    print(f"Successfully wrote popularity data for {len(metrics_by_game)} games to {output_file}")

if __name__ == "__main__":
    main()
