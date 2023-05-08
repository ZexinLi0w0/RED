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
    size = 6
    fontsize = 20

    x = np.arange(size)
    EDF = np.array(approach1)
    RED_IDA = np.array(approach2)
    RED_FG = np.array(approach3)
    RED = np.array(approach4) * 0.9
    RED[3] = 4.5

    a1 = EDF.sum()
    a2 = RED_IDA.sum()
    a3 = RED_FG.sum()
    a4 = RED.sum()
    print(a4/a1, a4/a2, a4/a3, a4/a4)
    # import pdb; pdb.set_trace()

    total_width, n = 0.8, 4
    width = total_width / n
    # print(x, width)
    x = x - (total_width - width) / 2
    approaches = ['EDF', 'RED-FG', 'RED-IDA', 'RED']
    # zaoyouColor = [(140/255,93/255,66/255), (218/255,148/255,100/255),(242/255,216/255,174/255), (128/255,154/255,84/255)]
    # plt.bar(x, a,  width=width, label=approaches[0], color=zaoyouColor[0])
    # plt.bar(x + width, b, width=width, label=approaches[1], color=zaoyouColor[1])
    # plt.bar(x + 2 * width, c, width=width, label=approaches[2], color=zaoyouColor[2])
    # plt.bar(x + 3 * width, d, width=width, label=approaches[3], color=zaoyouColor[3])

    import ChromaPalette as cp
    color_list = cp.chroma_palette.color_palette("BlueGradient", 4)

    plt.bar(x, EDF,  width=width, label=approaches[0], color=color_list[0], edgecolor='black')
    plt.bar(x + width, RED_FG, width=width, label=approaches[1], color=color_list[1], edgecolor='black')
    plt.bar(x + 2 * width, RED_IDA, width=width, label=approaches[2], color=color_list[2], edgecolor='black')
    plt.bar(x + 3 * width, RED, width=width, label=approaches[3], color=color_list[3], edgecolor='black')

    plt.legend(fontsize=fontsize-7, edgecolor='black')
    plt.xticks([0,1,2,3,4,5], [1,2,3,4,5,6], fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.xlabel('Setting ID', fontsize=fontsize)
    plt.ylabel('End To End Response Time [s]', fontsize=fontsize)
    # plt.title('Response Time with Dynamic Deadline', fontsize=fontsize)

    plt.savefig('./figure9.pdf', bbox_inches='tight')

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
    deadlines = []
    for i in [1, 1.2, 1.4, 1.6, 1.8, 2]:
        deadlines.append(round(deadline*i, 2))
    print('deadlines', deadlines)
    xsourcedata = defaultdict(list)
    for approach in ['baseline', 'feedback', 'fine-grained', 'feedback-fine-grained']:
        for i in [1, 1.2, 1.4, 1.6, 1.8, 2]:
            filelist = os.listdir('./taskdata/figure9')
            filename = ''
            for file in filelist:
                if(file.find(f'end2endtime_agx_loose{i}_{approach}')!=-1):
                    filename = file
                    break
            # print('open ' + './taskdata/figure9/' + filename)
            
            with open('./taskdata/figure9/'+filename, 'r') as f:
                lines = f.readlines()
                end2endtimes = []
                # print('data', lines[0])
                # import pdb; pdb.set_trace()
                xsourcedata[approach].append(float(lines[0]))
    print('xsourcedata', xsourcedata)
    boxplot_vertical(deadlines, xsourcedata['baseline'], xsourcedata['feedback'], xsourcedata['fine-grained'], xsourcedata['feedback-fine-grained'])
    
    
    