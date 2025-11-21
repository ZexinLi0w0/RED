#!/usr/bin/env python3
"""
Combine metrics from multiple device log files into a single summary.

Usage:
    python combine_metrics.py [--output combined_metrics.csv]
"""

import csv
import sys
import argparse
from pathlib import Path
from typing import List, Dict


def load_csv(csv_file: Path) -> List[Dict[str, str]]:
    """Load data from a CSV file."""
    results = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def combine_metrics(csv_files: List[Path], output_file: Path):
    """Combine metrics from multiple CSV files into one."""
    all_results = []
    
    for csv_file in csv_files:
        if not csv_file.exists():
            print(f"Warning: CSV file not found: {csv_file}", file=sys.stderr)
            continue
        
        print(f"Loading {csv_file.name}...")
        results = load_csv(csv_file)
        all_results.extend(results)
    
    if not all_results:
        print("No data to combine.", file=sys.stderr)
        return
    
    # Write combined results
    fieldnames = ['device', 'scenario', 'deadline', 'approach', 
                  'missing_deadline_rate', 'finished_time', 'deadline_time', 'qoe_score']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"\nCombined {len(all_results)} results from {len(csv_files)} files.")
    print(f"Output saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Combine metrics from multiple device CSV files'
    )
    parser.add_argument(
        '--csv-files',
        nargs='+',
        type=str,
        default=None,
        help='CSV files to combine (default: auto-detect *_new_scenarios_metrics.csv)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='combined_new_scenarios_metrics.csv',
        help='Output CSV file (default: combined_new_scenarios_metrics.csv)'
    )
    parser.add_argument(
        '--dir',
        type=str,
        default=None,
        help='Directory to search for CSV files (default: taskdata/new_scenarios)'
    )
    
    args = parser.parse_args()
    
    # Default to taskdata/new_scenarios if not specified
    if args.dir is None:
        script_dir = Path(__file__).parent
        root_dir = script_dir.parent
        search_dir = root_dir / 'taskdata' / 'new_scenarios'
    else:
        search_dir = Path(args.dir)
    
    output_file = Path(args.output)
    
    # Find CSV files
    if args.csv_files:
        csv_files = [Path(f) for f in args.csv_files]
    else:
        # Auto-detect metrics CSV files
        pattern = '*_new_scenarios_metrics.csv'
        csv_files = list(search_dir.glob(pattern))
        
        if not csv_files:
            print(f"No CSV files found matching pattern: {pattern}", file=sys.stderr)
            print(f"Searching in: {search_dir.absolute()}", file=sys.stderr)
            sys.exit(1)
    
    print(f"Found {len(csv_files)} CSV file(s) to combine:")
    for f in csv_files:
        print(f"  - {f}")
    
    combine_metrics(csv_files, output_file)


if __name__ == '__main__':
    main()

