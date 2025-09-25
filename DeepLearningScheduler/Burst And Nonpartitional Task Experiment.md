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
|Nano|Tight|Baseline|26.636419534683228|1.0000|1.0|
|Nano|Tight|RED|7.1950249671936035|0.9393939393939394|1.0|
|-----|---|---------------|--------|------|----|
|Orin|Tight|Baseline|x|x|x|
|Orin|Tight|RED|x|x|x|
|-----|---|---------------|--------|------|----|
|Apple Chip|Tight|Baseline|x|x|x|
|Apple Chip|Tight|RED|x|x|x|
|-----|---|---------------|--------|------|----|


## 实验日志

AGX Non-partitionable tasks 50%, EDF
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_test_non_partitionable_baseline_2025-09-25-09-23-08.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_test_non_partitionable_baseline_2025-09-25-09-23-08.pkl
INFO     [CTRL] Task End to End Finished time: 26.636419534683228
[STATS] Non-partitionable tasks: 35, Missing deadline rate: 1.0000
[STATS] Partitionable tasks: 35, Missing deadline rate: 1.0000
metrics finished time 26.636419534683228 7312.5
INFO     [CTRL] SubTask Missing deadline rate: 1.0
INFO     [CTRL] SubTask Average finished time: 0.34591717038835795
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```

AGX Non-partitionable tasks 50%, RED
```
INFO     [CTRL] All tasks finished
INFO     [CTRL] Saved end2end time to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/end2endtime_test_non_partitionable_feedback-fine-grained_2025-09-25-09-25-43.txt
INFO     [CTRL] Saved statistics to: /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/statistics_test_non_partitionable_feedback-fine-grained_2025-09-25-09-25-43.pkl
INFO     [CTRL] Task End to End Finished time: 7.1950249671936035
[STATS] Non-partitionable tasks: 6, Missing deadline rate: 5.3333
[STATS] Partitionable tasks: 4, Missing deadline rate: 7.5000
metrics finished time 7.1950249671936035 7312.5
INFO     [CTRL] SubTask Missing deadline rate: 0.9393939393939394
INFO     [CTRL] SubTask Average finished time: 0.36302230358123777
INFO     [CTRL] Task Metrics: (1, 1.0, 1.0)
```
