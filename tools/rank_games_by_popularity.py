#!/usr/bin/env python3
"""
Script to rank PortMaster games by popularity using IGDB metrics.
Reads the popularity metrics from port_popularity.json and ports_info.json
to create a ranked list of games based on popularity scores.

Usage:
    python rank_games_by_popularity.py          # Rank all games
    python rank_games_by_popularity.py -r       # Rank only ready-to-run games
    python rank_games_by_popularity.py -g puzzle  # Rank only puzzle games
    python rank_games_by_popularity.py -r -g arcade  # Rank only ready-to-run arcade games
"""

import json
import os
import argparse
from collections import defaultdict

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)  # Go up one level

# Set paths relative to the script location
POPULARITY_FILE = os.path.join(REPO_ROOT, "port_popularity.json")
PORTS_INFO_FILE = os.path.join(REPO_ROOT, "ports_info.json")

# Metric weights for scoring - based on engagement level
METRIC_WEIGHTS = {
    "1": 1.0,     # Visits - base weight
    "2": 2.0,     # Want to Play - medium interest
    "3": 5.0,     # Playing - highest current engagement
    "4": 4.0,     # Played - high historical engagement
    "5": 3.0,     # 24hr Peak Players
    "6": 3.0,     # Positive Reviews
    "7": 1.0,     # Negative Reviews (lower weight, still indicates engagement)
    "8": 2.0,     # Total Reviews
    "9": 4.0,     # Global Top Sellers
    "10": 2.5,    # Most Wishlisted Upcoming
}

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Rank PortMaster games by popularity metrics.'
    )
    parser.add_argument('-r', '--ready-to-run', action='store_true',
                      help='Filter for only ready-to-run games')
    parser.add_argument('-g', '--genre', type=str,
                      help='Filter for games of a specific genre (e.g., puzzle, action, rpg)')
    parser.add_argument('-o', '--output', type=str, default="ranked_ports.md",
                      help='Output file name')
    return parser.parse_args()

def load_data(file_path):
    """Load data from JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading data from {file_path}: {e}")
        return None

def get_port_data(ports_info, only_rtr=False, genre_filter=None):
    """Get data from ports_info.json.
    
    Args:
        ports_info (dict): Data loaded from ports_info.json
        only_rtr (bool): If True, only return ready-to-run games.
        genre_filter (str): If provided, only return games with this genre.
    """
    port_data = []
    
    # Check if the required data is available
    if not ports_info or 'ports' not in ports_info:
        print("Error: Required data not found in ports_info.json")
        return port_data
    
    # Process each port
    for port_name, port_info in ports_info.get('ports', {}).items():
        # Extract port name from zip filename (e.g., "celeste.zip" -> "celeste")
        port_key = port_name.replace('.zip', '')
        
        # Skip non-ready-to-run games if flag is set
        if only_rtr and not port_info.get('attr', {}).get('rtr', False):
            continue
        
        # Skip games that don't match the genre filter, if provided
        if genre_filter:
            genres = [g.lower() for g in port_info.get('attr', {}).get('genres', [])]
            if genre_filter.lower() not in genres:
                continue
        
        port_data.append({
            'name': port_key,
            'title': port_info.get('attr', {}).get('title', port_key),
            'rtr': port_info.get('attr', {}).get('rtr', False),
            'genres': port_info.get('attr', {}).get('genres', []),
            'availability': port_info.get('attr', {}).get('availability', None)
        })
    
    return port_data

def calculate_popularity_score(metrics):
    """Calculate a weighted popularity score from available metrics."""
    if not metrics:
        return 0
    
    score = 0
    for metric_id, value in metrics.items():
        # Apply weight based on metric type
        weight = METRIC_WEIGHTS.get(metric_id, 1.0)
        score += value * weight
    
    # Normalize by number of metrics and max weight to avoid bias toward games with more metrics
    # Division by max weight helps make scores more balanced
    max_weight = max(METRIC_WEIGHTS.values())
    avg_score = score / (len(metrics) * max_weight)
    
    return avg_score

def rank_ports_by_popularity(port_data, popularity_data):
    """Rank ports based on popularity metrics."""
    
    popularity_metrics = popularity_data.get('popularity_metrics', {})
    popularity_types = popularity_data.get('popularity_types', {})
    
    scored_ports = []
    
    for port in port_data:
        port_name = port['name']
        
        # Get metrics for this game - now directly by port name
        metrics = popularity_metrics.get(port_name, {})
        
        # Calculate popularity score
        score = calculate_popularity_score(metrics)
        
        # Convert metric IDs to names for easier reading
        named_metrics = {}
        for metric_id, value in metrics.items():
            metric_name = popularity_types.get(metric_id, f"Metric {metric_id}")
            named_metrics[metric_name] = value
        
        scored_ports.append({
            'name': port['name'],
            'title': port['title'],
            'score': score,
            'metrics': named_metrics,
            'rtr': port['rtr'],
            'genres': port['genres'],
            'availability': port['availability']
        })
    
    # Sort ports by score in descending order
    ranked_ports = sorted(scored_ports, key=lambda x: x['score'], reverse=True)
    
    return ranked_ports

def write_results_to_file(ranked_ports, output_file, only_rtr=False, genre_filter=None):
    """Write ranked ports to a file."""
    
    # Modify filename based on filters
    base, ext = os.path.splitext(output_file)
    filename_parts = [base]
    
    if only_rtr:
        filename_parts.append("rtr")
    
    if genre_filter:
        filename_parts.append(genre_filter.lower())
    
    if len(filename_parts) > 1:
        output_file = f"{filename_parts[0]}_{'_'.join(filename_parts[1:])}{ext}"
    
    with open(output_file, 'w') as f:
        title_parts = ["PortMaster Games Ranked by IGDB Popularity"]
        filter_parts = []
        
        if only_rtr:
            filter_parts.append("Ready-to-Run Only")
        
        if genre_filter:
            filter_parts.append(f"Genre: {genre_filter.capitalize()}")
        
        if filter_parts:
            title_parts.append(f"({', '.join(filter_parts)})")
        
        f.write(f"# {' '.join(title_parts)}\n\n")
        
        f.write("| Rank | Port Name | Title | Genres | RTR | Score | Metrics |\n")
        f.write("|------|-----------|-------|--------|-----|-------|--------|\n")
        
        for i, port in enumerate(ranked_ports, 1):
            metrics_str = ", ".join([f"{k}: {v:.2e}" for k, v in port['metrics'].items()])
            if not metrics_str:
                metrics_str = "No metrics available"
            
            genres_str = ", ".join(port['genres']) if port['genres'] else "N/A"
            rtr_str = "✓" if port['rtr'] else "✗"
            
            f.write(f"| {i} | {port['name']} | {port['title']} | {genres_str} | {rtr_str} | {port['score']:.6f} | {metrics_str} |\n")
    
    return output_file

def main():
    """Main function to rank ports by popularity."""
    args = parse_args()
    only_rtr = args.ready_to_run
    genre_filter = args.genre
    output_file = args.output
    
    filter_parts = []
    
    if only_rtr:
        filter_parts.append("Ready-to-Run")
    
    if genre_filter:
        filter_parts.append(f"Genre: {genre_filter}")
    
    if filter_parts:
        print(f"Filtering for {' and '.join(filter_parts)} games")
    
    print(f"Loading popularity data from {POPULARITY_FILE}")
    
    # Load popularity data
    popularity_data = load_data(POPULARITY_FILE)
    if not popularity_data:
        print("Failed to load popularity data. Exiting.")
        return
    
    print(f"Loading ports information from {PORTS_INFO_FILE}")
    
    # Load ports_info data
    ports_info = load_data(PORTS_INFO_FILE)
    if not ports_info:
        print("Failed to load ports information. Exiting.")
        return
    
    # Get port data
    port_data = get_port_data(ports_info, only_rtr, genre_filter)
    
    filter_desc = []
    if only_rtr:
        filter_desc.append("Ready-to-Run")
    if genre_filter:
        filter_desc.append(f"Genre: {genre_filter}")
    
    if filter_desc:
        filter_str = f" ({' & '.join(filter_desc)})"
    else:
        filter_str = ""
    
    print(f"Found {len(port_data)} ports{filter_str}")
    
    if len(port_data) == 0:
        print("No games match the specified filters. Exiting.")
        return
    
    # Rank ports by popularity
    ranked_ports = rank_ports_by_popularity(port_data, popularity_data)
    
    # Write results to file
    output_path = write_results_to_file(ranked_ports, output_file, only_rtr, genre_filter)
    print(f"Results written to {output_path}")
    
    # Print top 20 ports (or all if less than 20)
    max_display = min(20, len(ranked_ports))
    print(f"\nTop {max_display} Ports by Popularity{filter_str}:")
    for i, port in enumerate(ranked_ports[:max_display], 1):
        rtr_indicator = "✓" if port['rtr'] else "✗"
        print(f"{i}. [{rtr_indicator}] {port['title']} (Score: {port['score']:.6f})")

if __name__ == "__main__":
    main()
