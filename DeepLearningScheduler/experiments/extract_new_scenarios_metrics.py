#!/usr/bin/env python3
"""
Extract metrics from new scenarios log files.

Extracts:
- Missing deadline rate
- Average finished time
- QoE score

Usage:
    python extract_new_scenarios_metrics.py <log_file> [--output <output_file>]
"""

import re
import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def parse_log_file(log_file: Path) -> List[Dict[str, any]]:
    """
    Parse log file and extract metrics for each experiment.
    
    Returns a list of dictionaries, each containing:
    - device: Device name
    - scenario: Scenario name
    - deadline: Deadline type (Tight/Loose)
    - approach: Approach name
    - missing_deadline_rate: Missing deadline rate (float)
    - avg_finished_time: Average finished time (float)
    - qoe_score: QoE score (float)
    """
    results = []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        # Strip ANSI codes and whitespace
        line = strip_ansi_codes(lines[i]).strip()
        
        # Check if this is an experiment marker line
        if line.startswith('#'):
            # Parse experiment header: "# Device, Scenario, Deadline, Approach" or "# Device, Scenario, Approach" (old format)
            parts = [p.strip() for p in line[1:].split(',')]
            if len(parts) >= 3:
                device = parts[0]
                scenario = parts[1]
                # Handle both old format (3 fields) and new format (4 fields)
                if len(parts) >= 4:
                    deadline = parts[2]
                    approach = parts[3]
                else:
                    # Old format: try to infer deadline from next line (config file path)
                    deadline = 'Unknown'
                    approach = parts[2]
                    # Try to infer deadline from the next line if it contains config file path
                    if i + 1 < len(lines):
                        next_line = strip_ansi_codes(lines[i + 1]).strip()
                        if 'tight' in next_line.lower():
                            deadline = 'Tight'
                        elif 'loose' in next_line.lower():
                            deadline = 'Loose'
                
                # Look for metrics in the following lines
                missing_rate = None
                avg_time = None
                qoe_score = None
                
                # Search within the next 100 lines for this experiment's metrics
                for j in range(i + 1, min(i + 100, len(lines))):
                    metric_line = strip_ansi_codes(lines[j]).strip()
                    
                    # Extract missing deadline rate
                    if missing_rate is None:
                        match = re.search(r'SubTask Missing deadline rate:\s*([\d.]+)', metric_line)
                        if match:
                            missing_rate = float(match.group(1))
                    
                    # Extract average finished time
                    if avg_time is None:
                        match = re.search(r'SubTask Average finished time:\s*([\d.]+)', metric_line)
                        if match:
                            avg_time = float(match.group(1))
                    
                    # Extract QoE score
                    if qoe_score is None:
                        match = re.search(r'QoE Score:\s*([\d.]+)', metric_line)
                        if match:
                            qoe_score = float(match.group(1))
                    
                    # Stop if we hit the next experiment marker
                    if j < len(lines) - 1:
                        next_line = strip_ansi_codes(lines[j + 1]).strip()
                        if next_line.startswith('#'):
                            break
                
                # Only add if we found at least one metric
                if missing_rate is not None or avg_time is not None or qoe_score is not None:
                    results.append({
                        'device': device,
                        'scenario': scenario,
                        'deadline': deadline,
                        'approach': approach,
                        'missing_deadline_rate': missing_rate if missing_rate is not None else 'N/A',
                        'avg_finished_time': avg_time if avg_time is not None else 'N/A',
                        'qoe_score': qoe_score if qoe_score is not None else 'N/A'
                    })
        
        i += 1
    
    return results


def write_csv(results: List[Dict[str, any]], output_file: Path):
    """Write results to CSV file."""
    if not results:
        print("No results to write.", file=sys.stderr)
        return
    
    fieldnames = ['device', 'scenario', 'deadline', 'approach', 
                  'missing_deadline_rate', 'avg_finished_time', 'qoe_score']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Results written to {output_file}")


def print_table(results: List[Dict[str, any]]):
    """Print results as a formatted table."""
    if not results:
        print("No results found.")
        return
    
    # Calculate column widths
    headers = ['Device', 'Scenario', 'Deadline', 'Approach', 
               'Missing Deadline Rate', 'Avg Finished Time', 'QoE Score']
    col_widths = [len(h) for h in headers]
    
    for result in results:
        col_widths[0] = max(col_widths[0], len(str(result['device'])))
        col_widths[1] = max(col_widths[1], len(str(result['scenario'])))
        col_widths[2] = max(col_widths[2], len(str(result['deadline'])))
        col_widths[3] = max(col_widths[3], len(str(result['approach'])))
        col_widths[4] = max(col_widths[4], len(str(result['missing_deadline_rate'])))
        col_widths[5] = max(col_widths[5], len(str(result['avg_finished_time'])))
        col_widths[6] = max(col_widths[6], len(str(result['qoe_score'])))
    
    # Print header
    header_row = ' | '.join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_row)
    print('-' * len(header_row))
    
    # Print data rows
    for result in results:
        row = ' | '.join([
            str(result['device']).ljust(col_widths[0]),
            str(result['scenario']).ljust(col_widths[1]),
            str(result['deadline']).ljust(col_widths[2]),
            str(result['approach']).ljust(col_widths[3]),
            str(result['missing_deadline_rate']).ljust(col_widths[4]),
            str(result['avg_finished_time']).ljust(col_widths[5]),
            str(result['qoe_score']).ljust(col_widths[6])
        ])
        print(row)


def main():
    parser = argparse.ArgumentParser(
        description='Extract metrics from new scenarios log files'
    )
    parser.add_argument(
        'log_file',
        type=str,
        help='Path to the log file (e.g., mac_new_scenarios.log)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output CSV file path (default: <log_file>_metrics.csv)'
    )
    parser.add_argument(
        '--format',
        choices=['csv', 'table', 'both'],
        default='both',
        help='Output format: csv, table, or both (default: both)'
    )
    
    args = parser.parse_args()
    
    log_file = Path(args.log_file)
    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}", file=sys.stderr)
        sys.exit(1)
    
    # Parse log file
    print(f"Parsing {log_file}...")
    results = parse_log_file(log_file)
    
    if not results:
        print("No results found in log file.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(results)} experiment results.")
    
    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = log_file.parent / f"{log_file.stem}_metrics.csv"
    
    # Write output
    if args.format in ['csv', 'both']:
        write_csv(results, output_file)
    
    if args.format in ['table', 'both']:
        print("\nResults Table:")
        print_table(results)


if __name__ == '__main__':
    main()

