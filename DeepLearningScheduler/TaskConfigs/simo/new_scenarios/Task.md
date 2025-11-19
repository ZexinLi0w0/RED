# Background:
We have 3 devices, agx, mac, nano. In `TaskConfigs/simo`, we have different configs.
For each device and each scenario, we have loose dealline config and tight deadline config.
loose deadline config has loose running time for each subtask, normally it's 1.5x of the tight deadline config.

Here are tasks explaination:
1. L means LaneDetection
2. C means Control Autopilot
3. S means Segmentation
4. O means Object Detection


We can use these tasks to combine different scenarios.
Now we have 2 scenarios:
|Scenario|Stage1|Stage2|Stage3|
|:-------|:-----:|:-----:|:-----:|
|Obstacle-free cruising|L|S|C|
|Obstacle cruising|L|S+O|C|

The obstacle-free cruising config is here. The stage 1 is lane detection, it doesn't have dependencies. Lane detection use 1 as run argument. The stage 2 is segmentation, use 3 as run argument, it has dependency on stage 1(Task 1, LaneDetection). The stage 3 is control autopilot, use 2 as run argument, it has dependency on stage2(Task 3, Segmentation).
All tasks in the config have HandlerId 5 and Priority 1.
```
{
  "TaskName": "S1_Stage1_LaneDetection",
  "HandlerId": 5,
  "RunningTime": 1500,
  "Dependencies": [],
  "Priority": 1,
  "RunArgs": [1],
  "WorstRunningTime": 60
},
{
  "TaskName": "S1_Stage2_Segmentation",
  "HandlerId": 5,
  "RunningTime": 1500,
  "Dependencies": [1],
  "Priority": 1,
  "RunArgs": [3],
  "WorstRunningTime": 45
},
{
  "TaskName": "S1_Stage3_Control_Autopilot",
  "HandlerId": 5,
  "RunningTime": 1500,
  "Dependencies": [3],
  "Priority": 1,
  "RunArgs": [2],
  "WorstRunningTime": 45
}
```

The obstacle cruising config is here. The stage 1 is lane detection, it doesn't have dependencies. The stage 2 includes segmentation and object detection. Objection detection uses 4 as run argument. Both have dependency on stage 1(Task 1, LaneDetection). The stage 3 is control autopilot, it has dependency on stage2(Task 3 and Task 4, Segmentation and Object Detection).
```
{
  "TaskName": "S2_Stage1_LaneDetection",
  "HandlerId": 5,
  "RunningTime": 2100,
  "Dependencies": [],
  "Priority": 1,
  "RunArgs": [1],
  "WorstRunningTime": 60
},
[
  {
    "TaskName": "S2_Stage2_Segmentation",
    "HandlerId": 5,
    "RunningTime": 2100,
    "Dependencies": [1],
    "Priority": 1,
    "RunArgs": [3],
    "WorstRunningTime": 45
  },
  {
    "TaskName": "S2_Stage2_Object_Detection",
    "HandlerId": 5,
    "RunningTime": 2100,
    "Dependencies": [1],
    "Priority": 1,
    "RunArgs": [4],
    "WorstRunningTime": 60
  }
],
{
  "TaskName": "S2_Stage3_Control_Autopilot",
  "HandlerId": 5,
  "RunningTime": 2100,
  "Dependencies": [3, 4],
  "Priority": 1,
  "RunArgs": [2],
  "WorstRunningTime": 45
}
```

# Task: Create more simo configs for new Scenario

We want to add 3 new scenarios
|Scenario|Stage1|Stage2|Stage3|
|:-------|:-----:|:-----:|:-----:|
|Urban navigation| L+O | S+O | C |
|Emergency obstacle avoidance| O | L+S | C |
|Night driving| C | C | C |

You need to create 3*3 configs for each device(agx, mac, nano) and each scenario.
And for each config, you need to create tight and loose version.
All configs should be put in `TaskConfigs/simo/new_scenarios` folder.
The file name should be `{device}_[tight/loose]_{scenario}.json`.
You need to use the current configs to infer the running time for each taks on different devices.
