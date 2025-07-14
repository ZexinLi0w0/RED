import argparse
import pickle
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import math
import os
import json
import pandas as pd
import seaborn as sns
from matrics import throughput_score, RTscore, QoEScore

plt.rcParams['font.sans-serif']="Times New Roman"
plt.rcParams.update({'font.size': 5})

def lineplot(deadlines, xsourcedata):
    plt.figure(dpi=300, figsize=(3,2))
    leishenColor = [(53,38,96),(85,59,148),(152,114,202),(246,231,237),(95,32,61)]
    for i,each in enumerate(leishenColor):
        r,g,b = each
        leishenColor[i] = (r/255,g/255,b/255)
    approaches = ['Baseline', 'IDA', 'FG', 'RED']
    for i, approach in enumerate(approaches):
        plt.plot(deadlines, xsourcedata[approach], color=leishenColor[i], marker='D', markersize=1, label=approach)
    plt.legend()
    plt.show()

def boxplot_vertica1(matrics1_list, matrics2_list, matrics3_list, name="Video Inference"):
    """
    并列柱状图, Figure 7
    x轴，三个matrix score一组, 四组四个approach
    """
    plt.figure(dpi=300, figsize=(3,2))
    size = 5
    x = np.arange(size)
    a = np.array(matrics1_list) # matrics 1, throughput score
    b = np.array(matrics2_list) # matrics 2, RTscore
    # c = np.array(matrics3_list) # matrics 3, QoEScore

    total_width, n = 0.8, 2
    width = total_width / n
    x = x - (total_width - width) / 2
    approaches = ['2k','4k', '480', '720', '1080']
    zaoyouColor = [(218/255,148/255,100/255),(242/255,216/255,174/255), (128/255,154/255,84/255)]
    plt.bar(x, a,  width=width, color=zaoyouColor[0])
    plt.bar(x + width, b, width=width, color=zaoyouColor[1])
    # plt.bar(x + 2 * width, c, width=width, color=zaoyouColor[2])
    # plt.legend()
    # plt.ylim(0,1.0)
    plt.xticks([0-0.2,1-0.2,2-0.2,3-0.2, 4-0.2], approaches)
    plt.ylabel('Matrics Score')
    plt.title(f"{name}")

    plt.show()

def boxplot_vertical(avg_repsonse_time):
    plt.figure(dpi=300, figsize=(3, 2))
    size = 2
    x = np.arange(size)
    a = np.array(avg_repsonse_time)
    b = np.array([0,0,0,0,0])
    print(a,b)

    total_width, n = 0.8, 5
    width = total_width / n
    # print(x, width)
    x = x - (total_width - width) / 2
    approaches = ['2k','4k', '480', '720', '1080']
    zaoyouColor = [(91/255,74/255,71/255),(140/255,93/255,66/255), (218/255,148/255,100/255),(242/255,216/255,174/255), (128/255,154/255,84/255)]
    plt.bar(x, a,  width=width, label=approaches[0], color=zaoyouColor[0])
    plt.bar(x + width, b, width=width, label=approaches[1], color=zaoyouColor[1])
    # plt.bar(x + 2 * width, c, width=width, label=approaches[2], color=zaoyouColor[2])
    # plt.bar(x + 3 * width, d, width=width, label=approaches[3], color=zaoyouColor[3])
    # plt.bar(x + 4 * width, e, width=width, label=approaches[4], color=zaoyouColor[4])
    plt.legend(prop={'size': 4})    

    plt.xticks([0,1,2,3,4,5], approaches)
    plt.xlabel('Video Inference Type')
    plt.ylabel('End To End Response Time [ms]')
    # plt.title('Response Time with Dynamic Deadline')    

    plt.show()

if __name__ == "__main__":
    # test
    # Parse command line arguments
    # read data from config file
    names = ['agx']
    time_types = ['2k','4k', '480', '720', '1080']
    finished_time_list = defaultdict(list)
    for time_type in time_types:
        records = os.listdir(f"./taskdata/video_interference/{time_type}/")
        for record in records:
            with open(f'./taskdata/video_interference/{time_type}/{record}', "rb") as f:
                task_statistics = pickle.load(f)
                # calculate the max endtime and min start time in task_sta
                _minstarttime = math.inf
                _maxendtime = 0
                for task in task_statistics.values():
                    _minstarttime = min(_minstarttime, float(task['start_time']))
                    _maxendtime = max(_maxendtime, float(task['end_time']))
                finished_time = _maxendtime - _minstarttime
                finished_time_list[time_type].append(finished_time)
    print(f'finished_time: {finished_time_list}')
    avg_repsonse_time = []
    for key in finished_time_list:
        avg_repsonse_time.append(sum(finished_time_list[key]) / len(finished_time_list[key]))
    print(avg_repsonse_time)
    # boxplot_vertical(deadlines, xsourcedata['baseline'], xsourcedata['feedback'], xsourcedata['fine-grained'], xsourcedata['feedback-fine-grained'])
    boxplot_vertica1(avg_repsonse_time,[0,0,0,0,0],[0,0,0,0,0])
    
    