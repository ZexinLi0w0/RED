import argparse
import pickle
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import math
import os
import json
import pandas as pd
import seaborn as sns
from matrics import throughput_score, RTscore, QoEScore

plt.rcParams['font.sans-serif']="Times New Roman"
plt.rcParams.update({'font.size': 5})
fontsize = 20

def plot_legend():
    devices = ['EDF', 'RED-FG', 'RED-IDA', 'RED']
    # custom_colors = ['white', 'lightgray', 'darkgray', 'black']
    custom_colors = ['#000000', '#6C6C6C', '#BEBEBE', '#FFFFFF']

    # hatches = ['/', 'x', '\\', '+']  # Corrected hatches
    legend_patches = [
        mpatches.Patch(facecolor=custom_colors[i],
                       # hatch=hatches[i],
                       edgecolor='black',
                       label=device)
        for i, device in enumerate(devices)
    ]
    fig.legend(handles=legend_patches, loc='upper center', ncol=4, fontsize=fontsize, bbox_to_anchor=(0.5, 1.05),
               edgecolor='black')
def barplot_latency(source_data, ax):
    size = 4
    # fontsize = 20

    x = np.arange(size)
    EDF = np.array(source_data['EDF'])
    RED_FG = np.array(source_data['RED-FG'])
    RED_IDA = np.array(source_data['RED-IDA'])
    RED = np.array(source_data['RED'])

    all_data = np.stack((EDF, RED_FG, RED_IDA, RED), axis=0)

    a1 = EDF.sum()
    a3 = RED_IDA.sum()
    a2 = RED_FG.sum()
    a4 = RED.sum()
    print(a4 / a1, a4 / a2, a4 / a3, a4 / a4)

    total_width, n = 0.8, 4
    width = total_width / n
    x = x - (total_width - width) / 2
    approaches = ['EDF', 'RED-FG', 'RED-IDA', 'RED']

    color_list = ['#000000', '#6C6C6C', '#BEBEBE', '#FFFFFF']

    ax.bar(x, EDF, width=width, label=approaches[0], color=color_list[0], edgecolor='black')
    ax.bar(x + width, RED_FG, width=width, label=approaches[1], color=color_list[1], edgecolor='black')
    ax.bar(x + 2 * width, RED_IDA, width=width, label=approaches[2], color=color_list[2], edgecolor='black')
    ax.bar(x + 3 * width, RED, width=width, label=approaches[3], color=color_list[3], edgecolor='black')

    ax.set_xticks([])
    ax.tick_params(axis='y', labelsize=fontsize)
    ax.set_ylabel('{}'.format(source_data['metrics']), fontsize=fontsize)
    ax.set_title('{}'.format(source_data['title']), fontsize=fontsize)

    if 'info' in source_data.keys():
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["Light", "Medium", "Heavy", "Overload"], fontsize=fontsize)

        ax.text(0.5, -0.2, 'Workload Intensity', horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=fontsize)

# Deadline 1
latency_0 = {
    'EDF': [7.3063, 7.318774700164795, 7.7278337478637695, 13.54952716827392],
    'RED-FG': [7.305461168289185, 7.3330476284027, 7.335536003112793, 11.68731451034545],
    'RED-IDA': [7.0520966053, 7.260978937149048, 7.661771297454834, 13.6643815],
    'RED': [5.81512975692749, 6.2437968254089355, 6.2780749797821045, 7.27012777328],
    'metrics': "End To End Response Time [s]",
    'title': "7313ms Deadline",
}

# Deadline 2
latency_1 = {
    'EDF': [9.708656549453735, 9.738280773162842, 9.742734432220459, 13.6087603569],
    'RED-FG': [9.71573042869567, 9.738280773162842, 9.738394498825073, 11.6936745643615],
    'RED-IDA': [7.489305019378662, 7.400842189788818, 8.65004777, 13.627264499],
    'RED': [6.50918436050415, 6.353975296020508,7.1409008502960205, 9.3769302368],
    'metrics': "",
    'title': "9750ms Deadline",
}

# Deadline 3
latency_2 = {
    'EDF': [12.125782251358032, 12.12697029113769, 12.146758556365967, 13.6846032142639],
    'RED-FG': [12.122812747955322, 12.132575750350952, 12.146758556365967, 12.22124505],
    'RED-IDA': [7.20930314064, 7.25191116333007,12.146758556365967, 13.709626674],
    'RED': [5.723771333694458, 5.431160688, 7.450958251953125, 10.93888187408447],
    'metrics': "",
    'title': "12188ms Deadline",
}

deadline_0 = {
    'EDF': [57.14285714285714, 92.85714285714286, 100, 100],
    'RED-FG': [53.33, 90, 98.33333333333333, 100],
    'RED-IDA': [48.5714285, 82.85714285714286, 97.14285714285714, 100],
    'RED': [18.33333333333, 40, 50, 83.3333],
    'metrics': "Deadline Miss Rate [%]",
    'title': "",
}

deadline_1 = {
    'EDF': [15.71428571, 15.714285714285714, 28.57142857142857, 100],
    'RED-FG': [20, 18.3, 31.666666666666664, 100],
    'RED-IDA': [0, 1.4285714285714286, 0, 100],
    'RED': [3.333333333, 0, 5, 90],
    'metrics': "",
    'title': "",
}

deadline_2 = {
    'EDF': [5.714285714285714, 5.714285714285714, 15.714285714285714, 100],
    'RED-FG': [16.6666666, 16.666666666666, 38.333333333333336, 100],
    'RED-IDA': [0, 0, 0, 100],
    'RED': [0, 0, 0, 55],
    'metrics': "",
    'title': "",
}

def performance_analysis(deadline_missing_rate):
    A = 'RED'
    B = 'EDF'
    total = 0
    count = 0
    for workload in range(4):
        count += 1
        total += abs(deadline_missing_rate[A][workload] - deadline_missing_rate[B][workload]) / deadline_missing_rate[B][workload]
    print(f'{A} compared to {B} the avg performance improvement: ', total / count)
    return total / count
    
print(f'Missing Deadline Rate Decrease', (performance_analysis(deadline_0) + performance_analysis(deadline_1) + performance_analysis(deadline_2))/3)

def QoE(time_to_complete):
    lambda_param = 10
    return 1/(1 + math.pow(math.e, lambda_param) * max(0, time_to_complete))

def get_QoE_metrics_dict(latency_dict, deadline_dict, overall_deadline_time):
    res = {   
        'metrics': "QoE Score",
        'title': "",
        'info': "x",
    }
    for key in ['EDF', 'RED-FG', 'RED-IDA', 'RED']:
        # 0 - light, 1 - medium, 2 - heavy, 3 - overload
        res[key] = [0]*4
        for workload in range(0,4):
            res[key][workload] = QoE(latency_dict[key][workload] - overall_deadline_time)
    return res


qoemetrics_0 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "GPU Utilization [%]",
    'title': "",
    'info': "x",
}

qoemetrics_1 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "",
    'info': "x",
}

qoemetrics_2 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "",
    'info': "x",
}

figsize = (17, 8)
fig, axs = plt.subplots(2, 3, figsize=figsize)
plt.subplots_adjust(wspace=0.3)  # adjust the space between subplots

barplot_latency(latency_0, axs[0,0])
barplot_latency(latency_1, axs[0,1])
barplot_latency(latency_2, axs[0,2])
barplot_latency(deadline_0, axs[1,0])
barplot_latency(deadline_1, axs[1,1])
barplot_latency(deadline_2, axs[1,2])
# barplot_latency(qoemetrics_0, axs[2,0])
# barplot_latency(qoemetrics_1, axs[2,1])
# barplot_latency(qoemetrics_2, axs[2,2])

plot_legend()

plt.savefig('./ros_figures/ros.pdf', bbox_inches='tight')