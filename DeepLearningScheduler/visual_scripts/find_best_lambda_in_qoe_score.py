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

        # non-part %
        part_match = re.search(r"tasks ([0-9]+)%", title)
        nonpart = int(part_match.group(1)) if part_match else 0

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
            "nonpart": nonpart,
            "algo": algo,
            "finished": finished_time_sec,
            "deadline": deadline_ms
        })

    return parsed


def compute_qoe_grouped(experiments, lambda_device):
    groups = defaultdict(list)

    for exp in experiments:
        device = exp["device"]
        lambdas = lambda_device.get(device, [0.1])

        for lam in lambdas:
            qoe = QoEScore(exp["finished"], exp["deadline"], lam)
            groups[(device, exp["nonpart"])].append({
                "algo": exp["algo"],
                "lambda": lam,
                "qoe": qoe
            })

    return groups

def print_table(groups, lambda_device):
    devices = ["AGX", "Nano", "Mac"]

    for dev in devices:
        print("=" * 30, dev, "=" * 30)
        print()

        # 找这个设备的所有 nonpart
        dev_keys = [k for k in groups.keys() if k[0] == dev]
        nonparts = sorted(set(k[1] for k in dev_keys))

        for np in nonparts:
            print(f"Non-Partitionable {np}%")
            print(f"{'Algorithm':<12}{'λ':<10}{'QoE'}")

            # EDF first, then RED
            rows = sorted(groups[(dev, np)], key=lambda x: (x["algo"], x["lambda"]))

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
### AGX Non-partitionable tasks 0%, EDF

```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_non_partitionable_baseline_2025-09-25-11-13-19.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_non_partitionable_baseline_2025-09-25-11-13-19.pkl
INFO     [CTRL] Task End to End Finished time: 26.592604160308838
metrics finished time 26.592604160308838 17062.5
[DEBUG] QoE score calculation, finished_times:  [26.592604160308838] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.32350641659327917
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Non-partitionable tasks 0%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_non_partitionable_feedback-fine-grained_2025-09-25-11-17-24.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_non_partitionable_feedback-fine-grained_2025-09-25-11-17-24.pkl
INFO     [CTRL] Task End to End Finished time: 16.10952377319336
metrics finished time 16.10952377319336 17062.5
[DEBUG] QoE score calculation, finished_times:  [16.10952377319336] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.8166666666666667
INFO     [CTRL] SubTask Average finished time: 0.35806707713914954
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Non-partitionable tasks 50%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_non_partitionable_baseline_2025-09-25-11-02-27.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_non_partitionable_baseline_2025-09-25-11-02-27.pkl
INFO     [CTRL] Task End to End Finished time: 24.540611505508423
metrics finished time 24.540611505508423 17062.5
[DEBUG] QoE score calculation, finished_times:  [24.540611505508423] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.3151942798069545
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Non-partitionable tasks 50%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_non_partitionable_feedback-fine-grained_2025-09-25-11-09-52.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_non_partitionable_feedback-fine-grained_2025-09-25-11-09-52.pkl
INFO     [CTRL] Task End to End Finished time: 16.20795202255249
metrics finished time 16.20795202255249 17062.5
[DEBUG] QoE score calculation, finished_times:  [16.20795202255249] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.7910447761194029
INFO     [CTRL] SubTask Average finished time: 0.35578368450033254
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Non-partitionable tasks 100%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_non_partitionable_baseline_2025-09-25-10-44-07.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_non_partitionable_baseline_2025-09-25-10-44-07.pkl
INFO     [CTRL] Task End to End Finished time: 26.388326406478882
metrics finished time 26.388326406478882 17062.5
[DEBUG] QoE score calculation, finished_times:  [26.388326406478882] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.3421064853668213
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### AGX Non-partitionable tasks 100%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_agx_loose_non_partitionable_feedback-fine-grained_2025-09-25-10-48-50.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_agx_loose_non_partitionable_feedback-fine-grained_2025-09-25-10-48-50.pkl
INFO     [CTRL] Task End to End Finished time: 16.377562999725342
metrics finished time 16.377562999725342 17062.5
[DEBUG] QoE score calculation, finished_times:  [16.377562999725342] deadlines:  [17062.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.8285714285714286
INFO     [CTRL] SubTask Average finished time: 0.3373293876647949
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Non-partitionable tasks 100%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_non_partitionable_baseline_2025-09-29-03-03-16.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_non_partitionable_baseline_2025-09-29-03-03-16.pkl
INFO     [CTRL] Task End to End Finished time: 42.10524606704712
metrics finished time 42.10524606704712 39637.5
[DEBUG] QoE score calculation, finished_times:  [42.10524606704712] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.9714285714285714
INFO     [CTRL] SubTask Average finished time: 0.5515822614942278
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Non-partitionable tasks 100%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_non_partitionable_feedback-fine-grained_2025-09-29-03-18-49.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_non_partitionable_feedback-fine-grained_2025-09-29-03-18-49.pkl
INFO     [CTRL] Task End to End Finished time: 39.40302109718323
metrics finished time 39.40302109718323 39637.5
[DEBUG] QoE score calculation, finished_times:  [39.40302109718323] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.6428571428571429
INFO     [CTRL] SubTask Average finished time: 0.6031683401627974
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Non-partitionable tasks 50%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_non_partitionable_baseline_2025-09-29-03-34-52.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_non_partitionable_baseline_2025-09-29-03-34-52.pkl
INFO     [CTRL] Task End to End Finished time: 41.92612266540527
metrics finished time 41.92612266540527 39637.5
[DEBUG] QoE score calculation, finished_times:  [41.92612266540527] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.9857142857142858
INFO     [CTRL] SubTask Average finished time: 0.5331307445253645
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Non-partitionable tasks 50%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_non_partitionable_feedback-fine-grained_2025-09-29-03-38-08.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_non_partitionable_feedback-fine-grained_2025-09-29-03-38-08.pkl
INFO     [CTRL] Task End to End Finished time: 38.914307832717896
metrics finished time 38.914307832717896 39637.5
[DEBUG] QoE score calculation, finished_times:  [38.914307832717896] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.6811594202898551
INFO     [CTRL] SubTask Average finished time: 0.6031320903982434
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Non-partitionable tasks 0%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_non_partitionable_baseline_2025-09-29-03-59-00.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_non_partitionable_baseline_2025-09-29-03-59-00.pkl
INFO     [CTRL] Task End to End Finished time: 41.76921510696411
metrics finished time 41.76921510696411 39637.5
[DEBUG] QoE score calculation, finished_times:  [41.76921510696411] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.9857
INFO     [CTRL] SubTask Average finished time: 0.5617344038827079
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Nano Non-partitionable tasks 0%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_nano_loose_non_partitionable_feedback-fine-grained_2025-09-29-04-08-02.txt
INFO     [CTRL] Saved statistics to: /home/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_nano_loose_non_partitionable_feedback-fine-grained_2025-09-29-04-08-02.pkl
INFO     [CTRL] Task End to End Finished time: 37.4719443321228
metrics finished time 37.4719443321228 39637.5
[DEBUG] QoE score calculation, finished_times:  [37.4719443321228] deadlines:  [39637.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.6
INFO     [CTRL] SubTask Average finished time: 0.620154286330601
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Non-partitionable tasks 0%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_non_partitionable_baseline_2025-11-16-21-36-30.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_non_partitionable_baseline_2025-11-16-21-36-30.pkl
INFO     [CTRL] Task End to End Finished time: 5.640810966491699
metrics finished time 5.640810966491699 5662.5
[DEBUG] QoE score calculation, finished_times:  [5.640810966491699] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.17142857142857143
INFO     [CTRL] SubTask Average finished time: 0.05805956636156354
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Non-partitionable tasks 0%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_non_partitionable_feedback-fine-grained_2025-11-16-21-37-29.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_non_partitionable_feedback-fine-grained_2025-11-16-21-37-29.pkl
INFO     [CTRL] Task End to End Finished time: 3.630714178085327
metrics finished time 3.630714178085327 5662.5
[DEBUG] QoE score calculation, finished_times:  [3.630714178085327] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.0
INFO     [CTRL] SubTask Average finished time: 0.06007579962412516
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Non-partitionable tasks 50%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_non_partitionable_baseline_2025-11-16-21-38-24.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_non_partitionable_baseline_2025-11-16-21-38-24.pkl
INFO     [CTRL] Task End to End Finished time: 5.640009880065918
metrics finished time 5.640009880065918 5662.5
[DEBUG] QoE score calculation, finished_times:  [5.640009880065918] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.14285714285714285
INFO     [CTRL] SubTask Average finished time: 0.05744415351322719
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Non-partitionable tasks 50%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_non_partitionable_feedback-fine-grained_2025-11-16-21-39-38.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_non_partitionable_feedback-fine-grained_2025-11-16-21-39-38.pkl
INFO     [CTRL] Task End to End Finished time: 4.05480694770813
metrics finished time 4.05480694770813 5662.5
[DEBUG] QoE score calculation, finished_times:  [4.05480694770813] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.0
INFO     [CTRL] SubTask Average finished time: 0.06098394682913116
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Non-partitionable tasks 100%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_non_partitionable_baseline_2025-11-16-21-41-30.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_non_partitionable_baseline_2025-11-16-21-41-30.pkl
INFO     [CTRL] Task End to End Finished time: 5.641932725906372
metrics finished time 5.641932725906372 5662.5
[DEBUG] QoE score calculation, finished_times:  [5.641932725906372] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.15714285714285714
INFO     [CTRL] SubTask Average finished time: 0.05917684010096959
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

### Mac Non-partitionable tasks 100%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/end2endtime_mac_loose_non_partitionable_feedback-fine-grained_2025-11-16-21-42-02.txt
INFO     [CTRL] Saved statistics to: /Users/rentao/Documents/Github Projects/ATC23/DeepLearningScheduler/taskdata/statistics_mac_loose_non_partitionable_feedback-fine-grained_2025-11-16-21-42-02.pkl
INFO     [CTRL] Task End to End Finished time: 3.974318742752075
metrics finished time 3.974318742752075 5662.5
[DEBUG] QoE score calculation, finished_times:  [3.974318742752075] deadlines:  [5662.5] lambda_param:  10 QoE Score:  1.0
INFO     [CTRL] SubTask Missing deadline rate: 0.0
INFO     [CTRL] SubTask Average finished time: 0.05637404237474714
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