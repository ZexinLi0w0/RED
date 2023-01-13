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
    plt.figure(dpi=300, figsize=(3, 2))
    size = 6
    x = np.arange(size)
    a = np.array(approach1)
    b = np.array(approach2)
    c = np.array(approach3)
    d = np.array(approach4) 

    total_width, n = 0.8, 4
    width = total_width / n
    # print(x, width)
    x = x - (total_width - width) / 2
    approaches = ['Baseline', 'IDA', 'FG', 'RED']
    zaoyouColor = [(140/255,93/255,66/255), (218/255,148/255,100/255),(242/255,216/255,174/255), (128/255,154/255,84/255)]
    plt.bar(x, a,  width=width, label=approaches[0], color=zaoyouColor[0])
    plt.bar(x + width, b, width=width, label=approaches[1], color=zaoyouColor[1])
    plt.bar(x + 2 * width, c, width=width, label=approaches[2], color=zaoyouColor[2])
    plt.bar(x + 3 * width, d, width=width, label=approaches[3], color=zaoyouColor[3])
    plt.legend(prop={'size': 4})    
    plt.xticks([0,1,2,3,4,5], [1,2,3,4,5,6])
    plt.xlabel('Deadline (multiplier factor)')
    plt.ylabel('End To End Response Time [ms]')
    # plt.title('Response Time with Dynamic Deadline')    

    plt.show()

if __name__ == "__main__":
    # test
    # Parse command line arguments
    # read data from config file
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
                # hard-code to calculate the deadline
                deadline_time = dag_list[0][0]["RunningTime"]*running_time_factor + dag_list[1][0]["RunningTime"]*running_time_factor
                deadline = deadline_time/1000
    # print('[deadline for all tasks]',deadline)
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
                xsourcedata[approach].append(float(lines[0]))
    print('xsourcedata', xsourcedata)
    boxplot_vertical(deadlines, xsourcedata['baseline'], xsourcedata['feedback'], xsourcedata['fine-grained'], xsourcedata['feedback-fine-grained'])
    
    
    