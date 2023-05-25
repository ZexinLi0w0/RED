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
    fig.legend(handles=legend_patches, loc='upper center', ncol=4, fontsize=fontsize, bbox_to_anchor=(0.5, 0.97),
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


latency_0 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "End To End Response Time [s]",
    'title': "1000ms Deadline",
}

latency_1 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "2000ms Deadline",
}

latency_2 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "3000ms Deadline",
}

deadline_0 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "Deadline Miss Rate [%]",
    'title': "",
}

deadline_1 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "",
}

deadline_2 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "",
}

utilization_0 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "GPU Utilization [%]",
    'title': "",
    'info': "x",
}

utilization_1 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "",
    'info': "x",
}

utilization_2 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "",
    'title': "",
    'info': "x",
}

figsize = (17, 12)
fig, axs = plt.subplots(3, 3, figsize=figsize)
plt.subplots_adjust(wspace=0.3)  # adjust the space between subplots

barplot_latency(latency_0, axs[0,0])
barplot_latency(latency_1, axs[0,1])
barplot_latency(latency_2, axs[0,2])
barplot_latency(deadline_0, axs[1,0])
barplot_latency(deadline_1, axs[1,1])
barplot_latency(deadline_2, axs[1,2])
barplot_latency(utilization_0, axs[2,0])
barplot_latency(utilization_1, axs[2,1])
barplot_latency(utilization_2, axs[2,2])

plot_legend()

plt.savefig('./ros_figures/ros.pdf', bbox_inches='tight')