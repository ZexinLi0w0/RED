import re
import math
from collections import defaultdict

def QoEScore(finished_time_sec, deadline_ms, lambda_param):
    deadline_sec = deadline_ms / 1000.0
    miss = max(0, finished_time_sec - deadline_sec)
    return 1.0 / (1.0 + math.exp(lambda_param) * miss)

def parse_experiment_blocks(log_text):
    blocks = log_text.split("### ")
    parsed = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        title = lines[0].strip()

        # Device
        dev_match = re.match(r"(AGX|Nano|Mac)", title)
        if not dev_match:
            continue
        device = dev_match.group(1)

        # Determine task type: "Non-partitionable" or "Burst"
        task_type = None
        if "Non-partitionable" in title:
            task_type = "nonpart"
        elif "Burst" in title:
            task_type = "burst"
        else:
            # Skip if neither type is found
            continue

        # Extract percentage
        part_match = re.search(r"tasks ([0-9]+)%", title)
        percentage = int(part_match.group(1)) if part_match else 0

        # EDF or RED
        algo = "EDF" if "EDF" in title else "RED"

        # metrics line
        metric_match = re.search(r"metrics finished time ([0-9\.]+) ([0-9\.]+)", block)
        if not metric_match:
            continue

        finished_time_sec = float(metric_match.group(1))
        deadline_ms = float(metric_match.group(2))

        parsed.append({
            "device": device,
            "task_type": task_type,
            "percentage": percentage,
            "algo": algo,
            "finished": finished_time_sec,
            "deadline": deadline_ms
        })

    return parsed


def compute_qoe_grouped(experiments, lambda_device):
    groups = defaultdict(list)

    for exp in experiments:
        device = exp["device"]
        task_type = exp["task_type"]
        percentage = exp["percentage"]
        lambdas = lambda_device.get(device, [0.1])

        for lam in lambdas:
            qoe = QoEScore(exp["finished"], exp["deadline"], lam)
            groups[(device, task_type, percentage)].append({
                "algo": exp["algo"],
                "lambda": lam,
                "qoe": qoe
            })

    return groups

def print_table(groups, lambda_device):
    devices = ["AGX", "Nano", "Mac"]
    task_types = ["nonpart", "burst"]

    for dev in devices:
        print("=" * 30, dev, "=" * 30)
        print()

        # Process each task type separately
        for task_type in task_types:
            # Find all keys for this device and task type
            dev_keys = [k for k in groups.keys() if k[0] == dev and k[1] == task_type]
            if not dev_keys:
                continue
            
            percentages = sorted(set(k[2] for k in dev_keys))
            
            # Print task type header
            type_label = "Non-Partitionable" if task_type == "nonpart" else "Burst"
            print(f"--- {type_label} Tasks ---")
            print()

            for pct in percentages:
                key = (dev, task_type, pct)
                if key not in groups:
                    continue
                    
                print(f"{type_label} {pct}%")
                print(f"{'Algorithm':<12}{'λ':<10}{'QoE'}")

                # EDF first, then RED
                rows = groups[key]

                # Force order EDF -> RED
                algo_order = {"EDF": 0, "RED": 1}
                rows = sorted(rows, key=lambda x: (algo_order[x["algo"]], x["lambda"]))

                for r in rows:
                    print(f"{r['algo']:<12}{r['lambda']:<10}{r['qoe']:.6f}")
                print()

        print("=" * 75)
        print()

if __name__ == "__main__":
    # 读取你的实验文件
    log_text = """
### Mac Burst tasks 0%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [BURST] macOS GPU logging thread stopped.
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_burst_baseline_2025-11-17-03-06-13.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_burst_baseline_2025-11-17-03-06-13.pkl
INFO     [CTRL] Task End to End Finished time: 6.581241130828857
metrics finished time 6.581241130828857 5662.5
[DEBUG] QoE score calculation, finished_times:  [6.581241130828857] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.5125
INFO     [CTRL] SubTask Average finished time: 0.0748733937740326
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Burst tasks 0%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [BURST] macOS GPU logging thread stopped.
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_burst_fine-grained_2025-11-17-03-07-29.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_burst_fine-grained_2025-11-17-03-07-29.pkl
INFO     [CTRL] Task End to End Finished time: 6.57703709602356
metrics finished time 6.57703709602356 5662.5
[DEBUG] QoE score calculation, finished_times:  [6.57703709602356] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.4166666666666667
INFO     [CTRL] SubTask Average finished time: 0.08716992139816285
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Burst tasks 50%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [BURST] macOS GPU logging thread stopped.
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_burst_baseline_2025-11-17-03-08-40.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_burst_baseline_2025-11-17-03-08-40.pkl
INFO     [CTRL] Task End to End Finished time: 9.053339004516602
metrics finished time 9.053339004516602 5662.5
[DEBUG] QoE score calculation, finished_times:  [9.053339004516602] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.9833333333333333
INFO     [CTRL] SubTask Average finished time: 0.07529547810554504
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Burst tasks 50%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [BURST] macOS GPU logging thread stopped.
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_burst_fine-grained_2025-11-17-03-09-07.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_burst_fine-grained_2025-11-17-03-09-07.pkl
INFO     [CTRL] Task End to End Finished time: 6.576007843017578
metrics finished time 6.576007843017578 5662.5
[DEBUG] QoE score calculation, finished_times:  [6.576007843017578] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.6666666666666666
INFO     [CTRL] SubTask Average finished time: 0.08225281635920206
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Burst tasks 100%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [BURST] macOS GPU logging thread stopped.
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_burst_baseline_2025-11-17-03-09-46.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_burst_baseline_2025-11-17-03-09-46.pkl
INFO     [CTRL] Task End to End Finished time: 11.697674036026001
metrics finished time 11.697674036026001 5662.5
[DEBUG] QoE score calculation, finished_times:  [11.697674036026001] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.99375
INFO     [CTRL] SubTask Average finished time: 0.07298269122838974
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Burst tasks 100%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [BURST] macOS GPU logging thread stopped.
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_burst_fine-grained_2025-11-17-03-10-15.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_burst_fine-grained_2025-11-17-03-10-15.pkl
INFO     [CTRL] Task End to End Finished time: 6.577796697616577
metrics finished time 6.577796697616577 5662.5
[DEBUG] QoE score calculation, finished_times:  [6.577796697616577] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.08265920877456664
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Burst tasks 0%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_burst_baseline_2025-11-18-20-23-03.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_burst_baseline_2025-11-18-20-23-03.pkl
INFO     [CTRL] Task End to End Finished time: 31.599855184555054
metrics finished time 31.599855184555054 17062.5
[DEBUG] QoE score calculation, finished_times:  [31.599855184555054] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.3310242921113968
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Burst tasks 0%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_burst_fine-grained_2025-11-18-20-25-08.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_burst_fine-grained_2025-11-18-20-25-08.pkl
INFO     [CTRL] Task End to End Finished time: 26.67792534828186
metrics finished time 26.67792534828186 17062.5
[DEBUG] QoE score calculation, finished_times:  [26.67792534828186] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.3438823938369751
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Burst tasks 50%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_burst_baseline_2025-11-18-20-28-41.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_burst_baseline_2025-11-18-20-28-41.pkl
INFO     [CTRL] Task End to End Finished time: 46.337080001831055
metrics finished time 46.337080001831055 17062.5
[DEBUG] QoE score calculation, finished_times:  [46.337080001831055] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.33040637175242105
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Burst tasks 50%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_burst_fine-grained_2025-11-18-20-30-13.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_burst_fine-grained_2025-11-18-20-30-13.pkl
INFO     [CTRL] Task End to End Finished time: 25.61315608024597
metrics finished time 25.61315608024597 17062.5
[DEBUG] QoE score calculation, finished_times:  [25.61315608024597] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.3494880477587382
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Burst tasks 100%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_burst_baseline_2025-11-18-20-32-39.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_burst_baseline_2025-11-18-20-32-39.pkl
INFO     [CTRL] Task End to End Finished time: 58.43045997619629
metrics finished time 58.43045997619629 17062.5
[DEBUG] QoE score calculation, finished_times:  [58.43045997619629] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.3281223773956299
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Burst tasks 100%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_burst_fine-grained_2025-11-18-20-34-52.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_burst_fine-grained_2025-11-18-20-34-52.pkl
INFO     [CTRL] Task End to End Finished time: 27.30087924003601
metrics finished time 27.30087924003601 17062.5
[DEBUG] QoE score calculation, finished_times:  [27.30087924003601] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.34927869637807213
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Burst tasks 0%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_burst_baseline_2025-11-18-20-24-53.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_burst_baseline_2025-11-18-20-24-53.pkl
INFO     [CTRL] Task End to End Finished time: 48.83379054069519
metrics finished time 48.83379054069519 39637.5
[DEBUG] QoE score calculation, finished_times:  [48.83379054069519] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.520534685254097
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Burst tasks 0%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_burst_fine-grained_2025-11-18-20-26-50.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_burst_fine-grained_2025-11-18-20-26-50.pkl
INFO     [CTRL] Task End to End Finished time: 46.456401109695435
metrics finished time 46.456401109695435 39637.5
[DEBUG] QoE score calculation, finished_times:  [46.456401109695435] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.6009959618250529
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Burst tasks 50%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_burst_baseline_2025-11-18-20-29-49.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_burst_baseline_2025-11-18-20-29-49.pkl
INFO     [CTRL] Task End to End Finished time: 59.58103942871094
metrics finished time 59.58103942871094 39637.5
[DEBUG] QoE score calculation, finished_times:  [59.58103942871094] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.9916666666666667
INFO     [CTRL] SubTask Average finished time: 0.43872732321421304
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Burst tasks 50%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_burst_fine-grained_2025-11-18-20-31-40.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_burst_fine-grained_2025-11-18-20-31-40.pkl
INFO     [CTRL] Task End to End Finished time: 46.26708269119263
metrics finished time 46.26708269119263 39637.5
[DEBUG] QoE score calculation, finished_times:  [46.26708269119263] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.6019382357597352
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Burst tasks 100%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_burst_baseline_2025-11-18-20-34-06.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_burst_baseline_2025-11-18-20-34-06.pkl
INFO     [CTRL] Task End to End Finished time: 75.34471487998962
metrics finished time 75.34471487998962 39637.5
[DEBUG] QoE score calculation, finished_times:  [75.34471487998962] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.99375
INFO     [CTRL] SubTask Average finished time: 0.4298513576388359
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Burst tasks 100%, RED
```
INFO     [CTRL] All tasks finished
INFO     [BURST] System health monitoring stopped
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_burst_fine-grained_2025-11-18-20-35-42.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_burst_fine-grained_2025-11-18-20-35-42.pkl
INFO     [CTRL] Task End to End Finished time: 46.24245309829712
metrics finished time 46.24245309829712 39637.5
[DEBUG] QoE score calculation, finished_times:  [46.24245309829712] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.6000927925109864
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```
    """

    # lambda_device = {
    #     "AGX":  [0.01, 0.05, 0.1, 0.2],
    #     "Nano": [0.001, 0.005, 0.01, 0.02],
    #     "Mac":  [0.1, 0.2, 0.5, 1.0],
    # }
    lambda_device = {
      "AGX": [0.05],
      "Nano": [0.05],
      "Mac": [0.05],
    }

    experiments = parse_experiment_blocks(log_text)
    groups = compute_qoe_grouped(experiments, lambda_device)
    print_table(groups, lambda_device)