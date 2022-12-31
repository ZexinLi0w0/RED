import visdom
import argparse
import pickle
import numpy as np
from collections import defaultdict
from matplotlib import pyplot as plt
import math
import numpy as np

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
        if task['res'] == 'failure':
            missing_deadline_rate += 1
            missing_deadline_info[task["taskid"]] = 1
        else:
            finished_info[task['taskid']] = float(task['end_time']) - float(task['start_time'])
            avg_finished_time += finished_info[task['taskid']]
    avg_finished_time /= (len(task_statistics)-missing_deadline_rate)
    missing_deadline_rate /= len(task_statistics)
    return missing_deadline_rate, missing_deadline_info, avg_finished_time, finished_info
    
def task_scatter(task_statistics):
    """
    Use matlibplot to draw a scatter plot of the finished time of each task, X-axis is the timeline, Y-axis is the finished time.
    Finished task is marked as blue circle, missing deadline task is marked as red x.
    task_statistics: defaultdict(TaskFinishedObject), each dict contains the information of a task
    dict_values([{'taskid': 'Period[0]_#39_Id[1]', 'release_time': 0.9750000000000001, 'deadline': 0.9850000000000001, 'priority': 1, 'dependency': [], 'res': 'success', 'start_time': '0.9760010242462158', 'end_time': '0.9840006828308105'}])
    """
    # Create an empty list for the X and Y values of the finished tasks
    finished_x = []
    finished_y = []
    
    # Create an empty list for the X and Y values of the missed deadline tasks
    missed_x = []
    missed_y = []
    handlerid2color = defaultdict(float)
    points = defaultdict(list)

    # Iterate over the task statistics dictionary
    for task, task_info in task_statistics.items():
        # color = np.random.rand(3)
        # if(task_info["handler_id"] in handlerid2color):
        #     color = handlerid2color[task_info["handler_id"]]
        # else:
        #     handlerid2color[task_info["handler_id"]] = color
        
        # If the task was finished on time, add its start time and end time to the finished lists
        if task_info['res'] == 'success':
            end_time = float(task_info['end_time'])
            start_time = float(task_info['start_time'])
            finished_x.append(end_time)
            finished_y.append(end_time - start_time)
        # If the task missed its deadline, add its release time and deadline to the missed lists
        else:
            end_time = float(task_info['end_time'])
            start_time = float(task_info['start_time'])
            missed_x.append(end_time)
            missed_y.append(end_time - start_time)
    
    # Create a figure and axis object using Matplotlib
    fig, ax = plt.subplots()
    
    # Plot the finished tasks as blue circles
    ax.scatter(finished_x, finished_y, color='blue', marker='o', s = 2)
    
    # Plot the missed deadline tasks as red x's
    ax.scatter(missed_x, missed_y, color='red', marker='x', s = 2)
    
    # Set the X and Y axis labels
    ax.set_xlabel('Timeline')
    ax.set_ylabel('Finished Time')
    
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
    print(data)
    task_scatter(data)

