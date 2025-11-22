import re
import math
import sys
from pathlib import Path
from collections import defaultdict

def QoEScore(finished_time_sec, deadline_sec, lambda_param):
    """
    Calculate QoE score.
    Args:
        finished_time_sec: Finished time in seconds
        deadline_sec: Deadline in seconds
        lambda_param: Lambda parameter for QoE calculation
    """
    miss = max(0, finished_time_sec - deadline_sec)
    return 1.0 / (1.0 + math.exp(lambda_param) * miss)

def strip_ansi_codes(text):
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def parse_experiment_blocks(log_text):
    """
    Parse experiment blocks from log file.
    Expected format: # Device, Scenario, Deadline, Approach
    """
    # Split by lines starting with "# " (experiment headers)
    lines = log_text.split('\n')
    parsed = []
    current_block = []
    current_header = None
    
    for line in lines:
        line = strip_ansi_codes(line).strip()
        
        # Check if this is a new experiment header
        if line.startswith('# '):
            # Process previous block if exists
            if current_header and current_block:
                exp_data = parse_single_experiment(current_header, '\n'.join(current_block))
                if exp_data:
                    parsed.append(exp_data)
            
            # Start new block
            current_header = line[2:].strip()  # Remove "# "
            current_block = []
        elif current_header:
            current_block.append(line)
    
    # Process last block
    if current_header and current_block:
        exp_data = parse_single_experiment(current_header, '\n'.join(current_block))
        if exp_data:
            parsed.append(exp_data)
    
    return parsed

def parse_single_experiment(header, block_text):
    """
    Parse a single experiment block.
    Header format: "Mac, Urban navigation, Loose, Baseline"
    """
    # Parse header: Device, Scenario, Deadline, Approach
    parts = [p.strip() for p in header.split(',')]
    if len(parts) < 4:
        return None
    
    device = parts[0]
    scenario = parts[1]
    deadline_type = parts[2]  # Tight or Loose
    approach = parts[3]
    
    # Map approach names
    approach_map = {
        "Baseline": "Baseline",
        "RED-IDA": "RED-IDA",
        "RED-FG": "RED-FG",
        "RED": "RED"
    }
    approach = approach_map.get(approach, approach)
    
    # Find metrics line: "metrics finished time X Y"
    metric_match = re.search(r'metrics finished time ([0-9\.]+) ([0-9\.]+)', block_text)
    if not metric_match:
        return None
    
    finished_time_sec = float(metric_match.group(1))
    deadline_sec = float(metric_match.group(2))  # Already in seconds
    
    return {
        "device": device,
        "scenario": scenario,
        "deadline_type": deadline_type,
        "approach": approach,
        "finished": finished_time_sec,
        "deadline": deadline_sec
    }


def compute_qoe_grouped(experiments, lambda_values):
    """
    Group experiments and compute QoE for different lambda values.
    Groups by: (device, scenario, deadline_type, approach)
    """
    groups = defaultdict(list)

    for exp in experiments:
        device = exp["device"]
        scenario = exp["scenario"]
        deadline_type = exp["deadline_type"]
        approach = exp["approach"]
        
        # Compute QoE for each lambda value
        for lam in lambda_values:
            qoe = QoEScore(exp["finished"], exp["deadline"], lam)
            groups[(device, scenario, deadline_type, approach)].append({
                "lambda": lam,
                "qoe": qoe
            })

    return groups

def print_table(groups, lambda_values):
    """
    Print QoE results in a table format.
    """
    # Get unique devices, scenarios, deadline types, and approaches
    devices = sorted(set(k[0] for k in groups.keys()))
    scenarios = sorted(set(k[1] for k in groups.keys()))
    deadline_types = sorted(set(k[2] for k in groups.keys()))
    approaches = sorted(set(k[3] for k in groups.keys()))
    
    # Approach display order
    approach_order = {"Baseline": 0, "RED-IDA": 1, "RED-FG": 2, "RED": 3}
    approaches = sorted(approaches, key=lambda x: approach_order.get(x, 999))
    
    for dev in devices:
        print("=" * 80)
        print(f"Device: {dev}")
        print("=" * 80)
        print()
        
        for scenario in scenarios:
            print(f"  Scenario: {scenario}")
            print("-" * 80)
            
            for deadline_type in deadline_types:
                print(f"    Deadline: {deadline_type}")
                print()
                
                # Print header
                header = f"{'Approach':<15}"
                for lam in lambda_values:
                    header += f"{'λ=' + str(lam):<13}"
                print(header)
                print("-" * len(header))
                
                # Print each approach
                for approach in approaches:
                    key = (dev, scenario, deadline_type, approach)
                    if key not in groups:
                        continue
                    
                    row_data = groups[key]
                    # Sort by lambda
                    row_data = sorted(row_data, key=lambda x: x["lambda"])
                    
                    # Find best lambda (highest QoE) for highlighting
                    best_entry = max(row_data, key=lambda x: x["qoe"])
                    best_qoe = best_entry["qoe"]
                    
                    row = f"{approach:<15}"
                    for lam in lambda_values:
                        qoe = next((r["qoe"] for r in row_data if r["lambda"] == lam), None)
                        if qoe is not None:
                            # Highlight best QoE with asterisk
                            if abs(qoe - best_qoe) < 1e-6:
                                row += f"{qoe:>11.6f}* "
                            else:
                                row += f"{qoe:>12.6f} "
                        else:
                            row += f"{'N/A':>12} "
                    print(row)
                
                print()
        
        print()

if __name__ == "__main__":
    # Hard-coded log file path
    log_file_path = 'taskdata/new_scenarios/mac_new_scenarios.log'
    
    # Hard-coded lambda values to test
    lambda_values = [0.01]
    
    # Read log file
    log_path = Path(log_file_path)
    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reading log file: {log_path}")
    with open(log_path, 'r', encoding='utf-8') as f:
        log_text = f.read()
    
    # Parse experiments
    experiments = parse_experiment_blocks(log_text)
    print(f"Found {len(experiments)} experiments")
    print()
    
    if not experiments:
        print("No experiments found in log file!", file=sys.stderr)
        sys.exit(1)
    
    # Compute QoE for different lambda values
    print(f"Testing lambda values: {lambda_values}")
    print()
    
    groups = compute_qoe_grouped(experiments, lambda_values)
    print_table(groups, lambda_values)