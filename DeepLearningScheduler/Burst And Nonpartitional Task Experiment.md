# Mini Benchmark

再跑三个新的 mini benchmark. urber, emergency 和 night driving.


# Burst Task Experiment 

跑一组 benchmark, 不需要区分 tight/loose.
0%, 50%, 100% 不同的 burst task 比例

-----------------------------
|Device|DDL|Approach|EndToEnd Response Time|Missing DDL Rate|QoE|Description|
|-----|---|-------------|--------|------|----|------|
|Nano|Loose|Baseline|x|x|x|  |
|Nano|Loose|IDA|x|x|x|  |
|Nano|Loose|FG|x|x|x|  |
|Nano|Loose|RED|x|x|x|  |
|Nano|Tight|Baseline|x|x|x|  |
|Nano|Tight|IDA|x|x|x|  |
|Nano|Tight|FG|x|x|x|  |
|Nano|Tight|RED|x|x|x|  |
|-----|---|-------------|--------|------|----|------|
|Orin|Loose|Baseline|x|x|x|  |
|Orin|Loose|IDA|x|x|x|  |
|Orin|Loose|FG|x|x|x|  |
|Orin|Loose|RED|x|x|x|  |
|Orin|Tight|Baseline|x|x|x|  |
|Orin|Tight|IDA|x|x|x|  |
|Orin|Tight|FG|x|x|x|  |
|Orin|Tight|RED|x|x|x|  |
|-----|---|-------------|--------|------|----|------|
|Apple Chip|Loose|Baseline|x|x|x|  |
|Apple Chip|Loose|IDA|x|x|x|  |
|Apple Chip|Loose|FG|x|x|x|  |
|Apple Chip|Loose|RED|x|x|x|  |
|Apple Chip|Tight|Baseline|x|x|x|  |
|Apple Chip|Tight|IDA|x|x|x|  |
|Apple Chip|Tight|FG|x|x|x|  |
|Apple Chip|Tight|RED|x|x|x|  |
|-----|---|-------------|--------|------|----|------|



# Nonpartitional Task Experiment

Non-partitionable 不需要 tight/loose, 只需要跑一个 bench


-----------------------------
|Device|DDL|Approach|EndToEnd Response Time|Missing DDL Rate|QoE|
|-----|---|---------------|--------|------|----|
|Orin|Loose - 0% Non-partitionable|Baseline|26.592604160308838|1.0|1.0|
|Orin|Loose - 0% Non-partitionable|RED|16.10952377319336|0.8166666666666667|1.0|
|Orin|Loose - 50% Non-partitionable|Baseline|24.540611505508423|1.0|1.0|
|Orin|Loose - 50% Non-partitionable|RED|16.20795202255249|0.7910447761194029|1.0|
|Orin|Loose - 100% Non-partitionable|Baseline|26.388326406478882|1.0|1.0|
|Orin|Loose - 100% Non-partitionable|RED|16.377562999725342|0.8285714285714286|1.0|
|-----|---|---------------|--------|------|----|



## 实验日志

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