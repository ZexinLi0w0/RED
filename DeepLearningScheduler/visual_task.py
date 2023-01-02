import visdom
import argparse
import pickle
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import math

"""
Before running this script, you need to install visdom first and launch a visdom server in another shell.

# Launch a visdom.server

Open a terminal, run `python -m visdom.server` (in your conda virtual env)
Pay attension to you 8097 port, it needs to be occupied by visdom.
"""
WindowName = 'TaskProgress'

# data visulization, use scatter to show missing deadline rate and finished time of each tasks
def statistics_compution(task_statistics):
    """
    Calculate the statistics of tasks, including: missing deadline rate, finished time
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    # calculate the missing deadline rate
    missing_deadline_rate = 0
    missing_deadline_info = defaultdict(int)
    finished_info = defaultdict(float)
    avg_finished_time = 0
    for task in task_statistics.values():
        if task['res'] != 'success':
            missing_deadline_rate += 1
            missing_deadline_info[task["taskid"]] = 1
        else:
            finished_info[task['taskid']] = float(task['end_time']) - float(task['start_time'])
            avg_finished_time += finished_info[task['taskid']]
    avg_finished_time /= (len(task_statistics)-missing_deadline_rate)
    missing_deadline_rate /= len(task_statistics)
    return missing_deadline_rate, missing_deadline_info, avg_finished_time, finished_info
    
def task_scatter(task_statistics, datafile='taskdata.pkl'):
    """
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
        # If the task was finished on time, add its start time and end time to the finished lists
        if task_info['res'] == 'success':
            end_time = float(task_info['end_time'])
            release_time = float(task_info['release_time'])
            handler2points[handler_id]["finished_x"].append(end_time)
            handler2points[handler_id]["finished_y"].append(1000*(end_time - release_time))
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            end_time = float(task_info['end_time'])
            release_time = float(task_info['release_time'])
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(1000*(end_time - release_time))
        elif task_info["res"] == "skip":
            release_time = float(task_info['release_time'])
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(0)
    
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    finish_handles = []
    missing_handles = []
    skip_handles = []

    for handler_id in [1,2,3,4]:
        if(len(handler2points[handler_id]["finished_x"]) == 0 and len(handler2points[handler_id]["missing_x"]) == 0 and len(handler2points[handler_id]["skip_x"]) == 0):
            continue
        # Plot the finished tasks as blue circles
        finished_scatter = ax.scatter(handler2points[handler_id]["finished_x"], handler2points[handler_id]["finished_y"], c = handlerid2color[handler_id], marker='o', s = 15, label= f"{handler_id}")
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

    ax.legend(loc="upper right", title="Handler ID")
    # ax.legend(['o', 'x', '+'], ['Finished', 'Missed', 'Skip'], loc="upper right", title="Task Status")
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline')
    ax.set_ylabel('Response Time')
    plt.title("Dynamic Workloads Tasks Pipeline")
    
    # Show the plot
    plt.show()

    # plt.savefig(f'./taskdata_figure/{datafile}.pdf') 

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
            handler2points[handler_id]["finished_y"].append(end_time - release_time)
        # If the task missed its deadline, add its release time and deadline to the missed lists
        elif task_info['res'] == 'failure':
            handler2points[handler_id]["missing_x"].append(end_time)
            handler2points[handler_id]["missing_y"].append(end_time - release_time)
        elif task_info["res"] == "skip":
            handler2points[handler_id]["skip_x"].append(release_time)
            handler2points[handler_id]["skip_y"].append(0)
        # box data group by release time per seconds
        if(math.floor(release_time) >= len(handler2boxdata[handler_id])):
            handler2boxdata[handler_id].append([])
        handler2boxdata[handler_id][math.floor(release_time)].append(end_time - release_time)
    
    # print('handler box data', handler2boxdata)
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    finish_handles = []
    missing_handles = []
    skip_handles = []

    for handler_id in [2]:
        if(len(handler2points[handler_id]["finished_x"]) == 0 and len(handler2points[handler_id]["missing_x"]) == 0 and len(handler2points[handler_id]["skip_x"]) == 0):
            continue
        # Plot the finished tasks as blue circles
        
        ax.boxplot(handler2boxdata[handler_id])
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
    ax.set_xlabel('Timeline')
    ax.set_ylabel('Task Response Time')
    # ax.set_ylim(0, 0.05)
    plt.title("Async Inference Tasks")
    
    # Show the plot
    plt.show()


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



if __name__ == "__main__":
    # test
    # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--data", "-d", required=True, help="path of data file")
    # use pickle to load data
    args = parser.parse_args()
    data = pickle.load(open(args.data, "rb"))
    task_scatter(data, datafile=args.data)
    task_boxplot(data, datafile=args.data)

