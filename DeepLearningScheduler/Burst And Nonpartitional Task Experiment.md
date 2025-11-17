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
|AGX|Loose|Baseline|x|x|x|  |
|AGX|Loose|IDA|x|x|x|  |
|AGX|Loose|FG|x|x|x|  |
|AGX|Loose|RED|x|x|x|  |
|AGX|Tight|Baseline|x|x|x|  |
|AGX|Tight|IDA|x|x|x|  |
|AGX|Tight|FG|x|x|x|  |
|AGX|Tight|RED|x|x|x|  |
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

## 实验日志
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

# Nonpartitional Task Experiment

Non-partitionable 不需要 tight/loose, 只需要跑一个 bench


-----------------------------

|Device|DDL|Approach|EndToEnd Response Time|Missing DDL Rate|QoE|
|-----|---|---------------|--------|------|----|
|AGX|Loose - 0% Non-partitionable|Baseline|26.592604160308838|1.0|1.0|
|AGX|Loose - 0% Non-partitionable|RED|16.10952377319336|0.8166666666666667|1.0|
|AGX|Loose - 50% Non-partitionable|Baseline|24.540611505508423|1.0|1.0|
|AGX|Loose - 50% Non-partitionable|RED|16.20795202255249|0.7910447761194029|1.0|
|AGX|Loose - 100% Non-partitionable|Baseline|26.388326406478882|1.0|1.0|
|AGX|Loose - 100% Non-partitionable|RED|16.377562999725342|0.8285714285714286|1.0|
|-----|---|---------------|--------|------|----|
|Nano|Loose - 0% Non-partitionable|Baseline|41.76921510696411|0.9857|1.0|
|Nano|Loose - 0% Non-partitionable|RED|37.4719443321228|0.6|1.0|
|Nano|Loose - 50% Non-partitionable|Baseline|41.92612266540527|0.9857142857142858|1.0|
|Nano|Loose - 50% Non-partitionable|RED|38.914307832717896|0.6811594202898551|1.0|
|Nano|Loose - 100% Non-partitionable|Baseline|42.10524606704712|0.9714285714285714|1.0|
|Nano|Loose - 100% Non-partitionable|RED|39.40302109718323|0.6428571428571429|1.0|
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










### 实验数据转 Latex 表格

Based on the filled latex table, update data and address comment in main text. Make sure to check logic and make transition smooth. 

Table:
<Filled data table>

Text:
\begin{table}[!tbp]
\centering
\caption{End‑to‑end latency / deadline‑miss rate / QoE under different
non‑partitionable‑task ratios in obstacle‑free cruising scenarios.}
\label{tab:nonpartitionable}
\begin{tabular}{l|cc|cc|cc}
\hline
\multirow{2}{*}{Platform} & \multicolumn{2}{c|}{0\% Non‑Part.} &
                            \multicolumn{2}{c|}{50\% Non‑Part.} &
                            \multicolumn{2}{c}{100\% Non‑Part.} \\
\cline{2-7}
 & EDF & \tool & EDF & \tool & EDF & \tool \\
\hline
\multicolumn{7}{c}{End-to-end Latency} \\
\hline
Nano Orin & 41.77 & 37.47 & 41.93 & 38.91 & 42.11 & 39.40 \\
AGX Orin  & 26.59 & 16.11 & 24.54 & 16.21 & 26.39 & 16.38 \\
MacBook Pro   & 5.64  & 3.63  & 5.64  & 4.05  & 5.64  & 3.97  \\
\hline
\multicolumn{7}{c}{Deadline Miss Rate} \\
\hline
Nano Orin              & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
AGX Orin               & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
MacBook Pro   & 0.171 & 0.000 & 0.143 & 0.000 & 0.157 & 0.000 \\
\hline
\multicolumn{7}{c}{QoE} \\
\hline
Nano Orin              & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
AGX Orin               & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
MacBook Pro   & 1.0 & 1.0 & 1.0 & 1.0 & 1.0 & 1.0 \\
\hline
\end{tabular}
\end{table}