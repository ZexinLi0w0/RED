import argparse
import pickle
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import math
import json
import pandas as pd
import seaborn as sns
from pathlib import Path
from matrics import (
    DEFAULT_QOE_LAMBDA,
    DEADLINE_MISS_OUTCOMES,
    EXECUTED_OUTCOMES,
    QoEScore,
    RTscore,
    deadline_miss_rate_from_outcomes,
    throughput_score,
)
from task_generator import overall_deadline_seconds, timing_config_from_mapping


plt.rcParams['font.sans-serif']="Times New Roman"
plt.rcParams.update({'font.size': 8})

"""
Before running this script, you need to install visdom first and launch a visdom server in another shell.

# Launch a visdom.server

Open a terminal, run `python -m visdom.server` (in your conda virtual env)
Pay attension to you 8097 port, it needs to be occupied by visdom.
"""
WindowName = 'TaskProgress'

def ticks_merge(obj, item, tick, merge_tick = 1):
    """
    merge release_time within this tick like 1 second, 0.1 second
    """
    if(merge_tick == 1):
        obj[math.floor(tick)].append(item)
    elif(merge_tick in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]):
        obj[tick * 10 // (merge_tick*10)].append(item)
    else:
        obj[tick // merge_tick].append(item)

# data visulization, use scatter to show missing deadline rate and finished time of each tasks
def _resolve_task_config(task_config_path: str) -> Path:
    """
    Resolve the path to the task configuration file. The task_config_path argument
    can be a full/relative path or just the file name. We probe the common
    TaskConfigs directories to stay backward compatible with historical setups.
    """
    candidate = Path(task_config_path)
    search_roots = [
        Path("."),
        Path("./TaskConfigs"),
        Path("./TaskConfigs/simo"),
        Path("./TaskConfigs/simo/new_scenarios"),
    ]

    if candidate.is_file():
        return candidate

    for root in search_roots:
        maybe = root / task_config_path
        if maybe.is_file():
            return maybe

    raise FileNotFoundError(f"Unable to locate task config file: {task_config_path}")


def _overall_deadline_seconds(config: dict) -> float:
    """Return the same maximum absolute deadline used by task generation."""
    return overall_deadline_seconds(
        config.get("dag_list", []), timing_config_from_mapping(config)
    )


def statistics_compution(task_statistics, task_config_path='task_config.json', now_time = 0, task_start_time = 0):
    """
    Calculate the statistics of tasks, including: missing deadline rate, finished time
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    # Calculate task-level outcomes and execution latency. A skipped or
    # proactively dropped task did not execute, so it counts as a deadline miss
    # but not as a zero-duration latency sample.
    missing_deadline_info = defaultdict(int)
    finished_info = defaultdict(float)
    outcomes = []

    for task in task_statistics.values():
        outcome = task['res']
        outcomes.append(outcome)

        if outcome in EXECUTED_OUTCOMES:
            duration = float(task['end_time']) - float(task['start_time'])
            if duration < 0:
                raise ValueError(
                    f"task {task['taskid']} has end_time before start_time"
                )
            finished_info[task['taskid']] = duration

        if outcome in DEADLINE_MISS_OUTCOMES:
            missing_deadline_info[task["taskid"]] = 1

    missing_deadline_rate = deadline_miss_rate_from_outcomes(outcomes)
    avg_finished_time = (
        sum(finished_info.values()) / len(finished_info) if finished_info else 0.0
    )
    
    metrics1 = 1
    metrics2 = 0
    metrics3 = 0
    deadline_time = math.inf
    qoe_lambda = DEFAULT_QOE_LAMBDA
    # matrics calculation
    try:
        config_path = _resolve_task_config(task_config_path)
        with open(config_path, "r") as f:
            config = json.load(f)
        deadline_time = _overall_deadline_seconds(config)
        qoe_lambda = config.get("QoELambda", DEFAULT_QOE_LAMBDA)
        if "QoELambda" not in config:
            print(
                f"[WARN] Task config '{config_path}' has no QoELambda; "
                f"using legacy default {DEFAULT_QOE_LAMBDA}"
            )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[WARN] Failed to load task config '{task_config_path}' for metrics: {exc}")

    finished_time = now_time - task_start_time
    print('metrics finished time', finished_time, deadline_time)
    if math.isfinite(deadline_time) and deadline_time > 0:
        metrics2 = RTscore([finished_time], [deadline_time])
        metrics3 = QoEScore(
            [finished_time], [deadline_time], lambda_param=qoe_lambda
        )
        
    metrics = (metrics1, metrics2, metrics3)
    return missing_deadline_rate, missing_deadline_info, avg_finished_time, finished_info, metrics
    

def task_scatter(task_statistics, datafile='taskdata.pkl'):
    """
    Default version
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    handlerid2color = ["_","blue","red","orange","green","black","purple","magenta"]
    handler2points = defaultdict(dict)
    for handler_id in range(1,6):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': []
        }

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])
        # if(release_time<=1):
        #     continue
        # If the task was finished on time, add its start time and end time to the finished lists
        if task_info['res'] == 'success':
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(end_time - release_time)
    
    
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    finish_handles = []
    missing_handles = []
    skip_handles = []

    id2name = {
        1: "A",
        2: "B",
        3: "D",
        4: "C",
        5: "E"
    }

    for handler_id in [1,2,3,4,5]:
        total_tasks = (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]) +
                      len(handler2points[handler_id]["non_partitionable_finished_x"]) + len(handler2points[handler_id]["non_partitionable_missing_x"]) + len(handler2points[handler_id]["non_partitionable_skip_x"]))
        if(total_tasks == 0):
            continue
            
        # Plot the finished tasks as blue circles
        finished_scatter = ax.scatter(handler2points[handler_id]["finished_x"], handler2points[handler_id]["finished_y"], c = handlerid2color[handler_id], marker='o', s = 15, label= f"{id2name[handler_id]}")
        missing_scatter = ax.scatter(handler2points[handler_id]["missing_x"], handler2points[handler_id]["missing_y"], c = handlerid2color[handler_id], marker='x', s = 50)
        skiped_scatter = ax.scatter(handler2points[handler_id]["skip_x"], handler2points[handler_id]["skip_y"], c = handlerid2color[handler_id], marker='+', s = 50) 
        
        # Plot non-partitionable tasks with larger markers and different style
        if len(handler2points[handler_id]["non_partitionable_finished_x"]) > 0:
            ax.scatter(handler2points[handler_id]["non_partitionable_finished_x"], handler2points[handler_id]["non_partitionable_finished_y"], 
                      c = handlerid2color[handler_id], marker='s', s = 25, alpha=0.7, edgecolors='black', linewidth=1)
        if len(handler2points[handler_id]["non_partitionable_missing_x"]) > 0:
            ax.scatter(handler2points[handler_id]["non_partitionable_missing_x"], handler2points[handler_id]["non_partitionable_missing_y"], 
                      c = handlerid2color[handler_id], marker='X', s = 60, alpha=0.7, edgecolors='black', linewidth=1)
        if len(handler2points[handler_id]["non_partitionable_skip_x"]) > 0:
            ax.scatter(handler2points[handler_id]["non_partitionable_skip_x"], handler2points[handler_id]["non_partitionable_skip_y"], 
                      c = handlerid2color[handler_id], marker='*', s = 60, alpha=0.7, edgecolors='black', linewidth=1)
        
        # Calculate statistics including both task types
        partitionable_tasks = len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"])
        non_partitionable_tasks = len(handler2points[handler_id]["non_partitionable_finished_x"]) + len(handler2points[handler_id]["non_partitionable_missing_x"]) + len(handler2points[handler_id]["non_partitionable_skip_x"])
        
        missing_deadline_rate = (len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["non_partitionable_missing_x"])) / total_tasks
        finished_rate = (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["non_partitionable_finished_x"])) / total_tasks
        skip_rate = (len(handler2points[handler_id]["skip_x"]) + len(handler2points[handler_id]["non_partitionable_skip_x"])) / total_tasks
        
        finish_handles.append(finished_scatter)
        missing_handles.append(missing_scatter)
        skip_handles.append(skiped_scatter)
        print('Statistics of handler ', handler_id, ':')
        print('  Total tasks: ', total_tasks, '(partitionable: ', partitionable_tasks, ', non-partitionable: ', non_partitionable_tasks, ')')
        print('  missing deadline rate: ', missing_deadline_rate)
        print('  finished rate: ', finished_rate)
        print('  skip rate: ', skip_rate)

    ax.legend(loc="upper right", title="Task Name")
    # ax.legend(['Finished', 'Missed', 'Dropped'], loc="upper right", title="Task Status")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    # ax.set_ylim(0, 30)
    # ax.set_xlim(0,9)
    ax.set_xticks(np.arange(0, 10, 1))
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline [s]')
    ax.set_ylabel('Response Time [ms]')
    plt.title("Dynamic Workloads")
    
    # Show the plot
    plt.show()

def task_scatter1(task_statistics, datafile='taskdata.pkl'):
    """
    For case study 1
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    handlerid2color = ["_","blue","red","orange","green","black","purple","magenta"]
    handler2points = defaultdict(dict)
    for handler_id in range(1,5):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': []
        }

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])
        # if(release_time<=1):
        #     continue
        # If the task was finished on time, add its start time and end time to the finished lists
        if task_info['res'] == 'success':
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(end_time - release_time)
    
    
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    finish_handles = []
    missing_handles = []
    skip_handles = []

    id2name = {
        1: "A",
        2: "B",
        3: "D",
        4: "C"
    }

    for handler_id in [1,2,3,4]:
        if(len(handler2points[handler_id]["finished_x"]) == 0 and len(handler2points[handler_id]["missing_x"]) == 0 and len(handler2points[handler_id]["skip_x"]) == 0):
            continue
        # Plot the finished tasks as blue circles
        finished_scatter = ax.scatter(handler2points[handler_id]["finished_x"], handler2points[handler_id]["finished_y"], c = handlerid2color[handler_id], marker='o', s = 15, label= f"{id2name[handler_id]}")
        missing_scatter = ax.scatter(handler2points[handler_id]["missing_x"], handler2points[handler_id]["missing_y"], c = handlerid2color[handler_id], marker='x', s = 50)
        skiped_scatter = ax.scatter(handler2points[handler_id]["skip_x"], handler2points[handler_id]["skip_y"], c = handlerid2color[handler_id], marker='+', s = 50) 
        missing_deadline_rate = len(handler2points[handler_id]["missing_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finished_rate = len(handler2points[handler_id]["finished_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        skip_rate = len(handler2points[handler_id]["skip_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finish_handles.append(finished_scatter)
        missing_handles.append(missing_scatter)
        skip_handles.append(skiped_scatter)
        print('Statistics of handler ', handler_id, ':')
        print('missing deadline rate: ', missing_deadline_rate)
        print('finished rate: ', finished_rate)
        print('skip rate: ', skip_rate)

    # ax.legend(loc="upper right", title="Task Name")
    # ax.legend(['Finished', 'Missed', 'Dropped'], loc="upper right", title="Task Status")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    ax.set_ylim(0, 30)
    ax.set_xlim(0,9)
    ax.set_xticks(np.arange(0, 10, 1))
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline [s]')
    ax.set_ylabel('Response Time [ms]')
    plt.title("Dynamic Workloads")
    
    # Show the plot
    plt.show()

def task_scatter2(task_statistics, datafile='taskdata.pkl'):
    """
    For case study 2
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    handlerid2color = ["_","blue","red","orange","green","black","purple","magenta"]
    merge_tick = 0.2
    handler2points = defaultdict(dict)
    for handler_id in range(1,5):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': []
        }
    missing_and_drop_step1 = []
    missing_and_drop_step2 = []
    missing_and_drop_step3 = []
    missing_and_drop_persecond = defaultdict(list)
    success_persecond = defaultdict(list)
    for handler_id in range(1,5):
        missing_and_drop_persecond[handler_id] = defaultdict(list)
        success_persecond[handler_id] = defaultdict(list)
    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])

        # If the task was finished on time, add its start time and end time to the finished lists
        if task_info['res'] == 'success':
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
            ticks_merge(success_persecond[handler_id], 1, release_time, merge_tick=merge_tick)
            # success_persecond[handler_id][math.floor(release_time)].append(1)
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
            ticks_merge(missing_and_drop_persecond[handler_id], 1, release_time, merge_tick=merge_tick)
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(end_time - release_time)
            ticks_merge(missing_and_drop_persecond[handler_id], 1, release_time, merge_tick=merge_tick)
    
    for handler_id in range(1,5):
        print(f'missing and drop rate per sercond handler[{handler_id}]:')
        for tick in success_persecond[handler_id].keys():
            if(len(success_persecond[handler_id][tick]) + len(missing_and_drop_persecond[handler_id][tick]) == 0):
                print(f'no task on running on {tick*merge_tick} second')
                continue
            print(f'missing rate on {round(tick*merge_tick, 4)} second: {round(len(missing_and_drop_persecond[handler_id][tick])/(len(success_persecond[handler_id][tick]) + len(missing_and_drop_persecond[handler_id][tick])), 4)}')
    
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    finish_handles = []
    missing_handles = []
    skip_handles = []

    id2name = {
        1: "A",
        2: "C",
        3: "D",
        4: "B"
    }

    for handler_id in [1,2,3,4]:
        if(len(handler2points[handler_id]["finished_x"]) == 0 and len(handler2points[handler_id]["missing_x"]) == 0 and len(handler2points[handler_id]["skip_x"]) == 0):
            continue
        # Plot the finished tasks as blue circles
        finished_scatter = ax.scatter(handler2points[handler_id]["finished_x"], handler2points[handler_id]["finished_y"], c = handlerid2color[handler_id], marker='o', s = 15, label= f"{id2name[handler_id]}")
        missing_scatter = ax.scatter(handler2points[handler_id]["missing_x"], handler2points[handler_id]["missing_y"], c = handlerid2color[handler_id], marker='x', s = 50)
        skiped_scatter = ax.scatter(handler2points[handler_id]["skip_x"], handler2points[handler_id]["skip_y"], c = handlerid2color[handler_id], marker='+', s = 50) 
        missing_deadline_rate = len(handler2points[handler_id]["missing_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finished_rate = len(handler2points[handler_id]["finished_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        skip_rate = len(handler2points[handler_id]["skip_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finish_handles.append(finished_scatter)
        missing_handles.append(missing_scatter)
        skip_handles.append(skiped_scatter)
        print('Statistics of handler ', handler_id, ':')
        print('missing deadline rate: ', missing_deadline_rate)
        print('finished rate: ', finished_rate)
        print('skip rate: ', skip_rate)

    # ax.legend(loc="upper right", title="Task Name")
    # ax.legend(['Finished', 'Missed', 'Dropped'], loc="upper right", title="Task Status")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    ax.set_ylim(0, 50)
    ax.set_xlim(0, 1)
    # ax.set_xticks(np.arange(0, 10, 1))
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline [s]')
    ax.set_ylabel('Response Time [ms]')
    plt.title("Dependent Inference")
    
    # Show the plot
    plt.show()

def task_scatter3(task_statistics, datafile='taskdata.pkl'):
    """
    For approach 1,2,3,4
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    Non-partitionable tasks are marked with larger markers and different colors.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    handlerid2color = ["_","blue","red","orange","green","magenta","purple","black"]
    handler2points = defaultdict(dict)
    for handler_id in range(1,6):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': [],
            'non_partitionable_finished_x': [],
            'non_partitionable_finished_y': [],
            'non_partitionable_missing_x': [],
            'non_partitionable_missing_y': [],
            'non_partitionable_skip_x': [],
            'non_partitionable_skip_y': []
        }

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])
        is_non_partitionable = task_info.get('is_non_partitionable', False)
        
        # if(release_time<=1):
        #     continue
        # If the task was finished on time, add its start time and end time to the finished lists
        print('[debug] time: ',task_info, end_time - release_time)
        if task_info['res'] == 'success':
            if is_non_partitionable:
                handler2points[handler_id]["non_partitionable_finished_x"].append(end_time)
                handler2points[handler_id]["non_partitionable_finished_y"].append(1000*(end_time - release_time))
            else:
                handler2points[handler_id]["finished_x"].append(end_time)
                handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            if is_non_partitionable:
                handler2points[handler_id]["non_partitionable_missing_x"].append(end_time)
                handler2points[handler_id]["non_partitionable_missing_y"].append(1000*(end_time - release_time))
            else:
                handler2points[handler_id]["missing_x"].append(end_time)
                handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            if is_non_partitionable:
                handler2points[handler_id]["non_partitionable_skip_x"].append(release_time)
                handler2points[handler_id]["non_partitionable_skip_y"].append(end_time - release_time)
            else:
                handler2points[handler_id]["skip_x"].append(release_time)
                handler2points[handler_id]["skip_y"].append(end_time - release_time)
    
    
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    finish_handles = []
    missing_handles = []
    skip_handles = []

    id2name = {
        1: "A",
        2: "B",
        3: "D",
        4: "C",
        5: "E"
    }

    for handler_id in [1,2,3,4,5]:
        if(len(handler2points[handler_id]["finished_x"]) == 0 and len(handler2points[handler_id]["missing_x"]) == 0 and len(handler2points[handler_id]["skip_x"]) == 0):
            continue
        # Plot the finished tasks as blue circles
        finished_scatter = ax.scatter(handler2points[handler_id]["finished_x"], handler2points[handler_id]["finished_y"], c = handlerid2color[handler_id], marker='o', s = 15, label= f"{id2name[handler_id]}")
        missing_scatter = ax.scatter(handler2points[handler_id]["missing_x"], handler2points[handler_id]["missing_y"], c = handlerid2color[handler_id], marker='x', s = 50)
        skiped_scatter = ax.scatter(handler2points[handler_id]["skip_x"], handler2points[handler_id]["skip_y"], c = handlerid2color[handler_id], marker='+', s = 50) 
        missing_deadline_rate = len(handler2points[handler_id]["missing_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finished_rate = len(handler2points[handler_id]["finished_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        skip_rate = len(handler2points[handler_id]["skip_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finish_handles.append(finished_scatter)
        missing_handles.append(missing_scatter)
        skip_handles.append(skiped_scatter)
        print('Statistics of handler ', handler_id, ':')
        print('missing deadline rate: ', missing_deadline_rate)
        print('finished rate: ', finished_rate)
        print('skip rate: ', skip_rate)

    # ax.legend(loc="upper right", title="Task Name")
    # ax.legend(['Finished', 'Missed', 'Dropped'], loc="upper right", title="Task Status")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    # ax.set_ylim(0, 30)
    # ax.set_xlim(0,9)
    ax.set_xticks(np.arange(0, 10, 1))
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline [s]')
    ax.set_ylabel('Response Time [ms]')
    plt.title("Approach")
    
    # Show the plot
    plt.show()

def task_boxplot(task_statistics, datafile='taskdata.pkl'):
    """
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    handlerid2color = ["_","blue","red","orange","purple","black","cyan","magenta"]
    handler2points = defaultdict(dict)
    handler2boxdata = defaultdict(dict)
    for handler_id in range(1,5):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': []
        }
        handler2boxdata[handler_id] = []

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        # If the task was finished on time, add its start time and end time to the finished lists
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])
        if task_info['res'] == 'success':
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(0)
        # box data group by release time per seconds
        if(math.floor(release_time) >= len(handler2boxdata[handler_id])):
            handler2boxdata[handler_id].append([])
        # 按release time每秒聚类
        handler2boxdata[handler_id][math.floor(release_time)].append(1000*(end_time - release_time))
    
    fig, ax = plt.subplots()
    # print('handler box data', handler2boxdata)
    # Create a figure and axis object using Matplotlib
    finish_handles = []
    missing_handles = []
    skip_handles = []

    for handler_id in [1,2,3,4]:
        if(len(handler2points[handler_id]["finished_x"]) == 0 and len(handler2points[handler_id]["missing_x"]) == 0 and len(handler2points[handler_id]["skip_x"]) == 0):
            continue
        # Plot the finished tasks as blue circles
        
        ax.boxplot(handler2boxdata[handler_id], showmeans = True, showcaps = True)
        # ax.set_xticklabels(range(1,len(handler2boxdata[handler_id])))

        missing_deadline_rate = len(handler2points[handler_id]["missing_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finished_rate = len(handler2points[handler_id]["finished_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        skip_rate = len(handler2points[handler_id]["skip_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        print('Statistics of handler ', handler_id, ':')
        print('missing deadline rate: ', missing_deadline_rate)
        print('finished rate: ', finished_rate)
        print('skip rate: ', skip_rate)

    # ax.legend(loc="upper right", title="Handler ID")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline [s]')
    ax.set_ylabel('Response Time [ms]')
    # ax.set_ylim(0, 30)
    plt.title("Async Inference Task 1")
    
    # Show the plot
    plt.show()

    # plt.savefig(f'./taskdata_figure/{datafile}.pdf') 

def task_boxplot_221(task_statistics, datafile='taskdata.pkl'):
    """
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    handlerid2color = ["_","blue","red","orange","purple","black","cyan","magenta"]
    handler2points = defaultdict(dict)
    handler2boxdata = defaultdict(dict)
    for handler_id in range(1,5):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': []
        }
        handler2boxdata[handler_id] = []

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        # If the task was finished on time, add its start time and end time to the finished lists
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])
        if task_info['res'] == 'success':
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(0)
        # box data group by release time per seconds
        if(math.floor(release_time) >= len(handler2boxdata[handler_id])):
            handler2boxdata[handler_id].append([])
        # 按release time每秒聚类
        handler2boxdata[handler_id][math.floor(release_time)].append(1000*(end_time - release_time))
    
    # Create a figure and axis object using Matplotlib
    finish_handles = []
    missing_handles = []
    skip_handles = []

    handler_id = 1
        
    # Plot the finished tasks as blue circles
    fig, ax = plt.subplots()
    ax.boxplot(handler2boxdata[handler_id], showmeans = True, showcaps = True)
    # plt.set_xticklabels(range(1,len(handler2boxdata[handler_id])))

    missing_deadline_rate = len(handler2points[handler_id]["missing_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
    finished_rate = len(handler2points[handler_id]["finished_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
    skip_rate = len(handler2points[handler_id]["skip_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
    print('Statistics of handler ', handler_id, ':')
    print('missing deadline rate: ', missing_deadline_rate)
    print('finished rate: ', finished_rate)
    print('skip rate: ', skip_rate)

    handler_id = 2
    # Plot the finished tasks as blue circles
    fig, ax = plt.subplots()
    ax.boxplot(handler2boxdata[handler_id], showmeans = True, showcaps = True)
    # ax.set_xticklabels(range(1,len(handler2boxdata[handler_id])))

    missing_deadline_rate = len(handler2points[handler_id]["missing_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
    finished_rate = len(handler2points[handler_id]["finished_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
    skip_rate = len(handler2points[handler_id]["skip_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
    print('Statistics of handler ', handler_id, ':')
    print('missing deadline rate: ', missing_deadline_rate)
    print('finished rate: ', finished_rate)
    print('skip rate: ', skip_rate)


    # ax.legend(loc="upper right", title="Handler ID")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline [s]')
    ax.set_ylabel('Response Time [ms]')
    # ax.set_ylim(0, 0.05)
    plt.title("Async Inference Tasks")
    
    # Show the plot
    plt.show()

    # plt.savefig(f'./taskdata_figure/{datafile}.pdf')

def boxplot_vertical(matrics1_list, matrics2_list, matrics3_list, name="Figure 6 1/4"):
    """
    并列柱状图, Figure 6主图
    x轴，三个matrix score一组, 四组四个approach
    """
    plt.figure(dpi=300, figsize=(3,2))
    size = 4
    x = np.arange(size)
    a = np.array(matrics1_list) # matrics 1, throughput score
    b = np.array(matrics2_list) # matrics 2, RTscore
    c = np.array(matrics3_list) # matrics 3, QoEScore
    print(c)

    total_width, n = 0.8, 3
    width = total_width / n
    x = x - (total_width - width) / 2
    zaoyouColor = [(218/255,148/255,100/255),(242/255,216/255,174/255), (128/255,154/255,84/255)]
    plt.bar(x, a,  width=width, label='Throughput Score', color=zaoyouColor[0])
    plt.bar(x + width, b, width=width, label='RT Score', color=zaoyouColor[1])
    plt.bar(x + 2 * width, c, width=width, label='QoE Score', color=zaoyouColor[2])
    # plt.legend()
    plt.ylim(0,1.0)
    plt.xticks([0,1,2,3], ['Baseline', 'IDA', 'FG', 'RED'])
    plt.ylabel('Matrics Score')
    plt.title(f"{name}")

    plt.show()
    

def figure6(deadline, name):
    # TODO: add name(agx, orin, nano, tx2) as key for matrics
    matrics1_data = {
        "tight": [],
        "loose": []
    } # loose 4 approaches for matrics1, tight 4 approaches for matrics1
    matrics2_data = {
        "tight": [],
        "loose": []
    }
    matrics3_data = {
        "tight": [],
        "loose": []
    }
    time_constrains = ['tight', 'loose']
    task = ['baseline', 'progress_tracker', 'fine_grained', 'REDdrop']
    basepath = f'./taskdata/{name}_exp1/processed_data/'
    # get min response time
    min_response_time = math.inf
    for time_constrain_type in time_constrains:
        for task_type in task:
            filepath = f'{basepath}{name}_{time_constrain_type}_{task_type}.txt'
            with open(filepath, 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    min_response_time = min(min_response_time, float(line))
    
    # combine these to generate file path
    for time_constrain_type in time_constrains:
        for task_type in task:
            filepath = f'{basepath}{name}_{time_constrain_type}_{task_type}.txt'
            with open(filepath, 'r+') as f:
                # read each line
                lines = f.readlines()
                finished_times = []
                
                for line in lines:
                    # print('finished time: ', float(line))
                    finished_times.append(float(line))
                deadline_times = [deadline[name][time_constrain_type]/1000]*len(finished_times)
                a = throughput_score(finished_times, min_latency=min_response_time)
                b = RTscore(finished_times, deadline_times)
                c = QoEScore(finished_times, deadline_times)
                
                # TODO: add name as key for matrics
                matrics1_data[time_constrain_type].append(a)
                matrics2_data[time_constrain_type].append(b)
                matrics3_data[time_constrain_type].append(c)

                # print(f'[{name}_{time_constrain_type}_{task_type}]')
                # print('throughput score: ', a, "RT score: ", b, "QoE score: ", c)
    
    def matrics_performance(matrics, time_constrain_type):
        return {
            "IDA": f"{round((matrics[time_constrain_type][1] - matrics[time_constrain_type][0])*100, 2)}%",
            "FG": f"{round((matrics[time_constrain_type][2] - matrics[time_constrain_type][0])*100, 2)}%",
            "RED": f"{round((matrics[time_constrain_type][3] - matrics[time_constrain_type][0])*100, 2)}%"
        }
    # matrics performance calculation
    for time_constrain_type in time_constrains:
        print('-'*50)
        print(name.upper(), time_constrain_type)
        print('Throughput Improv: ',matrics_performance(matrics1_data, time_constrain_type))
        print('RTScore Improv: ', matrics_performance(matrics2_data, time_constrain_type))
        print('QoEScore Improv: ', matrics_performance(matrics3_data, time_constrain_type))
    # print(f"matrics all: {matrics1_data}, {matrics2_data}, {matrics3_data}")

    # draw matrics figure 6
    for time_constrain_type in time_constrains:
        # TODO: add name as key for matrics
        boxplot_vertical(matrics1_data[time_constrain_type], matrics2_data[time_constrain_type], matrics3_data[time_constrain_type], name=f"{name.upper()} {time_constrain_type}")

def visual_task_blocks(tasks):    
    vis = visdom.Visdom(env=WindowName)
    rows = []
    # max handler
    Y = []
    for i in range(5):
        rows.append([])
        Y.append('Handler' + str(i))
    Text = []    
    max_column = 0
    for task in tasks:
        # 获取 task 的开始时间和结束时间
        start = task['ReleaseTime']
        end = task['Deadline']
        # 获取 task 的 id
        _id = task['TaskId']
        handler_id = int(task["HandlerId"])
        # 将数据添加到 X，Y 和 Text 中
        rows[handler_id - 1].append(end - start) # bar length
        max_column = max(len(rows[handler_id - 1]), max_column)
        Text.append(_id)
    
    for r in rows:
        while(len(r) < max_column):
            r.append(0)

    # 将数据转化为 numpy 数组
    X = np.array(rows)
    Y = np.array(Y)
    # Text = np.array(Text)
    print(X.shape, Y.shape, len(Text))
    # print(X, Y, Text)

    # 使用 Visdom 画出块状图
    vis.bar(
        X=X,
        Y=Y,
        opts=dict(
            title = WindowName,
            width = 1000,
            height = 800,
            showlegend = True,
            xlabel = 'HandlerId',
            ylabel = 'TimeLine',
            ytick = True,
            ytickstep = 0.03,
            legend = Text,
            stacked = True            
        )
    )

def task_plotline(task_statistics, datafile='taskdata.pkl'):
    """
    For case study 2
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    handlerid2color = ["_","blue","red","orange","green","black","purple","magenta"]
    handler2points = defaultdict(dict)
    for handler_id in range(1,5):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': []
        }

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])
        # if(release_time<=1):
        #     continue
        # If the task was finished on time, add its start time and end time to the finished lists
        if task_info['res'] == 'success':
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(end_time - release_time)        
    
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    finish_handles = []
    missing_handles = []
    skip_handles = []

    id2name = {
        1: "A",
        2: "C",
        3: "D",
        4: "B"
    }

    for handler_id in [1,2,3,4]:
        if(len(handler2points[handler_id]["finished_x"]) == 0 and len(handler2points[handler_id]["missing_x"]) == 0 and len(handler2points[handler_id]["skip_x"]) == 0):
            continue
        # Plot the finished tasks as blue circles
        ax.plot(handler2points[handler_id]["finished_x"], handler2points[handler_id]["finished_y"], c = handlerid2color[handler_id], marker='o', label= f"{id2name[handler_id]}")
        ax.plot(handler2points[handler_id]["missing_x"], handler2points[handler_id]["missing_y"], c = handlerid2color[handler_id], marker='x')
        ax.plot(handler2points[handler_id]["skip_x"], handler2points[handler_id]["skip_y"], c = handlerid2color[handler_id], marker='+') 
        missing_deadline_rate = len(handler2points[handler_id]["missing_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        finished_rate = len(handler2points[handler_id]["finished_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        skip_rate = len(handler2points[handler_id]["skip_x"]) / (len(handler2points[handler_id]["finished_x"]) + len(handler2points[handler_id]["missing_x"]) + len(handler2points[handler_id]["skip_x"]))
        
        print('Statistics of handler ', handler_id, ':')
        print('missing deadline rate: ', missing_deadline_rate)
        print('finished rate: ', finished_rate)
        print('skip rate: ', skip_rate)

    # ax.legend(loc="upper right", title="Task Name")
    # ax.legend(['Finished', 'Missed', 'Dropped'], loc="upper right", title="Task Status")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    ax.set_ylim(0, 50)
    ax.set_xlim(0,1)
    # ax.set_xticks(np.arange(0, 10, 1))
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline [s]')
    ax.set_ylabel('Response Time [ms]')
    plt.title("Dependent Inference")
    
    # Show the plot
    plt.show()

def task_boxplot_seaborn(task_statistics, datafile=''):
    handlerid2color = ["_","blue","red","orange","green","black","purple","magenta"]
    handler2points = defaultdict(dict)
    handler2boxdata = defaultdict(list)
    for handler_id in range(1,5):
        handler2points[handler_id] = {
            'finished_x': [],
            'finished_y': [],
            'missing_x': [],
            'missing_y': [],
            'skip_x': [],
            'skip_y': []
        }

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        handler_id = task_info["handler_id"]
        release_time = float(task_info['release_time'])
        end_time = float(task_info['end_time'])
        # If the task was finished on time, add its start time and end time to the finished lists
        if task_info['res'] == 'success':
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(end_time - release_time)   
        # if(math.floor(release_time) >= len(handler2boxdata[handler_id])):
        #     handler2boxdata[handler_id].append([])

        handler2boxdata["handler_id"].append("A" if handler_id == 1 else "B")
        handler2boxdata["response_time"].append(1000*(end_time - release_time))
        
        handler2boxdata["release_time"].append(int((release_time  * 10) // 2))
    
    # print(handler2boxdata)
    handler2dataframe = pd.DataFrame(handler2boxdata)
    # print(handler2dataframe.head(10))
    sns.boxplot(x="release_time", y="response_time", hue="handler_id", data=handler2dataframe)
    plt.xlim(-0.5, 15.5)
    plt.ylim(0, 20)
    plt.legend(loc="upper right", title="Task Type")
    plt.title("Independent Inference")
    plt.xlabel("Timeline")
    plt.ylabel("Response Time [ms]")
    plt.show()

if __name__ == "__main__":
    # test
    # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--data", "-d", required=False, help="path of data file")
    # use pickle to load data
    args = parser.parse_args()
    if(args.data is not None):
        data = pickle.load(open(args.data, "rb"))
    # task_scatter2(data, datafile=args.data)
    # task_scatter3(data, datafile=args.data)
    # read data from config file
    # names = ['agx', 'orin', 'tx2', 'nano']
    names = ['orin']
    time_types = ['tight', 'loose']
    standard_deadline = defaultdict(dict)
    for name in names:
        for time_type in time_types:
            with open(f"./TaskConfigs/simo/{name}_{time_type}.json", "r") as f:
                config = json.load(f)
                dag_list = config["dag_list"]
                running_time_factor = 1
                if("RunningTimeFactor" in config):
                    running_time_factor = config["RunningTimeFactor"]
                # hard-code to calculate the deadline
                deadline_time = dag_list[0][0]["RunningTime"]*running_time_factor + dag_list[1][0]["RunningTime"]*running_time_factor
                standard_deadline[name][time_type] = deadline_time
    print('[deadline for all tasks]',standard_deadline)

    # print(standard_deadline)
    for name in names:
        figure6(standard_deadline, name)

    # boxplot_vertical([1],[2])
