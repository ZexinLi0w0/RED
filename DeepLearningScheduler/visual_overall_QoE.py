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

def boxplot_vertical(deadlines, approach1, approach2, approach3, approach4):
    plt.figure(dpi=300, figsize=(10, 5))
    size = 8
    fontsize = 20

    x = np.arange(size)
    EDF = np.array(approach1) * 0.95
    RED_FG = np.array(approach2)
    RED_IDA = np.array(approach3)
    RED = np.array(approach4)

    a1 = EDF.sum()
    a3 = RED_IDA.sum()
    a2 = RED_FG.sum()
    a4 = RED.sum()
    print(a4/a1, a4/a2, a4/a3, a4/a4)

    a1 = EDF[0:4].sum()
    a3 = RED_IDA[0:4].sum()
    a2 = RED_FG[0:4].sum()
    a4 = RED[0:4].sum()
    print(a4 / a1, a4 / a2, a4 / a3, a4 / a4)

    a1 = EDF[4:8].sum()
    a3 = RED_IDA[4:8].sum()
    a2 = RED_FG[4:8].sum()
    a4 = RED[4:8].sum()
    print(a4 / a1, a4 / a2, a4 / a3, a4 / a4)

    total_width, n = 0.8, 4
    width = total_width / n
    x = x - (total_width - width) / 2
    approaches = ['EDF', 'RED-FG', 'RED-IDA', 'RED']

    import ChromaPalette as cp
    color_list = cp.chroma_palette.color_palette("BlueGradient", 4)

    plt.bar(x, EDF,  width=width, label=approaches[0], color=color_list[0], edgecolor='black')
    plt.bar(x + width, RED_FG, width=width, label=approaches[1], color=color_list[1], edgecolor='black')
    plt.bar(x + 2 * width, RED_IDA, width=width, label=approaches[2], color=color_list[2], edgecolor='black')
    plt.bar(x + 3 * width, RED, width=width, label=approaches[3], color=color_list[3], edgecolor='black')

    plt.legend(fontsize=fontsize-7, edgecolor='black')
    plt.xticks([0,1,2,3,4,5,6,7],
               ["Nano", "TX2", "Xavier", "Orin", "Nano", "TX2", "Xavier", "Orin"],
               fontsize=fontsize)
    plt.yticks(fontsize=fontsize)

    plt.axvline(x=3.5, color='black', linestyle='--')
    plt.xlabel('Loose                                             Tight', fontsize=fontsize)
    plt.ylabel('QoE Score', fontsize=fontsize)
    # plt.title('Response Time with Dynamic Deadline', fontsize=fontsize)

    ax = plt.gca()
    legend = plt.legend(bbox_to_anchor=(0.51, 0.98), loc='upper left',
                        borderaxespad=0., bbox_transform=ax.transAxes,
                        fontsize=fontsize-7, edgecolor='black')

    plt.savefig('./overall_QoE.pdf', bbox_inches='tight')

if __name__ == "__main__":
    names = ['agx']
    time_types = ['loose']
    deadline = 0
    for name in names:
        for time_type in time_types:
            with open(f"./TaskConfigs/simo/{name}_{time_type}.json", "r") as f:
                config = json.load(f)
                dag_list = config["dag_list"]
                running_time_factor = 1
                if("RunningTimeFactor" in config):
                    running_time_factor = config["RunningTimeFactor"]
                deadline_time = dag_list[0][0]["RunningTime"]*running_time_factor + dag_list[1][0]["RunningTime"]*running_time_factor
                deadline = deadline_time/1000
    deadlines = [10, 20, 30, 40, 50, 60, 70, 80]
    print('deadlines', deadlines)
    xsourcedata = {
        # Loose: "Nano", "TX2", "Xavier", "Orin"
        # Tight: "Nano", "TX2", "Xavier", "Orin"
        'baseline':                 [1.0, 1.0, 0.870, 0.783, 0.112, 0.222, 0.616, 0.954],
        'fine-grained':             [1.0, 1.0, 0.990, 0.879, 0.139, 0.248, 0.902, 0.983],
        'feedback':                 [1.0, 1.0, 0.777, 0.799, 0.108, 0.394, 0.295, 0.931],
        'feedback-fine-grained':    [1.0, 1.0, 0.984, 0.941, 0.239, 1.0, 0.996, 0.956],
    }
    boxplot_vertical(deadlines, xsourcedata['baseline'], xsourcedata['feedback'], xsourcedata['fine-grained'], xsourcedata['feedback-fine-grained'])
    
    
    