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
    methods = ['EDF', 'RED-FG', 'RED-IDA', 'RED']
    # custom_colors = ['white', 'lightgray', 'darkgray', 'black']
    # hatches = ['/', 'x', '\\', '+']  # Corrected hatches

    custom_colors = ['#000000', '#6C6C6C', '#BEBEBE', '#FFFFFF']
    legend_patches = [
        mpatches.Patch(facecolor=custom_colors[i],
                       # hatch=hatches[i],
                       edgecolor='black',
                       label=method)
        for i, method in enumerate(methods)
    ]
    fig.legend(handles=legend_patches, loc='upper center', ncol=4, fontsize=fontsize, bbox_to_anchor=(0.5, 1.2),
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

    import ChromaPalette as cp

    color_list = cp.chroma_palette.color_palette("BlueGradient", 4)
    color_list = ['#000000', '#6C6C6C', '#BEBEBE', '#FFFFFF']

    ax.bar(x, EDF, width=width, label=approaches[0], color=color_list[0], edgecolor='black')
    ax.bar(x + width, RED_FG, width=width, label=approaches[1], color=color_list[1], edgecolor='black')
    ax.bar(x + 2 * width, RED_IDA, width=width, label=approaches[2], color=color_list[2], edgecolor='black')
    ax.bar(x + 3 * width, RED, width=width, label=approaches[3], color=color_list[3], edgecolor='black')

    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(["Nano", "TX2", "Xavier", "Orin"], fontsize=fontsize)
    ax.tick_params(axis='y', labelsize=fontsize)

    if source_data['metrics'] == "QoE Score" or source_data['metrics'] == "Deadline Miss Rate [%]":
        ymin = max(all_data.min() - 0.1, 0.0)
        ymax = min(all_data.max() + 0.1, 1.0)
        ax.set_ylim([ymin, ymax])

    ax.set_ylabel('{}'.format(source_data['metrics']), fontsize=fontsize)
    # print(source_data['title'])
    ax.set_title('{}'.format(source_data['title']), fontsize=fontsize)

latency_loose = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "End To End Response Time [s]",
    'title': "Loose Deadline",
}

latency_tight = {
    'EDF': [10.304, 9.511, 7.128, 2.503],
    'RED-FG': [9.814, 9.516, 6.630, 2.975],
    'RED-IDA': [10.585, 9.109, 8.314, 2.424],
    'RED': [8.647, 7.972, 6.405, 2.535],
    'metrics': "End To End Response Time [s]",
    'title': "Tight Deadline",
}

deadline_loose = {
    # 'EDF': [0.385, 0.157, 0.985, 0.885],
    # 'RED-FG': [0.5, 0.216, 0.971, 0.816],
    # 'RED-IDA': [0.328, 0.034, 0.616, 0.828],
    # 'RED': [0.2, 0.033, 0.366, 0.55],
    'EDF': [0.157, 0.385, 0.985, 0.985],
    'RED-FG': [0.216, 0.5, 0.971, 0.916],
    'RED-IDA': [0.034, 0.328, 0.616, 0.828],
    'RED': [0.033, 0.2, 0.366, 0.55],
    'metrics': "Deadline Miss Rate [%]",
    'title': "Loose Deadline",
}

deadline_tight = {
    'EDF': [1.0, 1.0, 0.971, 1.0],
    'RED-FG': [0.985, 1.0, 0.955, 0.953],
    'RED-IDA': [0.9, 0.933, 0.935, 0.911],
    'RED': [0.466, 0.583, 0.633, 0.9],
    'metrics': "Deadline Miss Rate [%]",
    'title': "Tight Deadline",
}

QoE_loose = {
    'EDF': [0.888, 0.912, 0.870, 0.783],
    'RED-FG': [0.912, 0.933, 0.990, 0.879,],
    'RED-IDA': [0.955, 0.988, 0.777, 0.799],
    'RED': [1.0, 1.0, 0.984, 0.941],
    'metrics': "QoE Score",
    'title': "Loose Deadline",
}

QoE_tight = {
    'EDF': [0.113, 0.222, 0.616, 0.954],
    'RED-FG': [0.108, 0.248, 0.295, 0.931],
    'RED-IDA': [0.140, 0.395, 0.902, 0.956],
    'RED': [0.240, 1.0, 0.996, 0.984],
    'metrics': "QoE Score",
    'title': "Tight Deadline",
}

figsize = (35, 4)
fig, axs = plt.subplots(1, 6, figsize=figsize)
plt.subplots_adjust(wspace=0.3)  # adjust the space between subplots

barplot_latency(latency_loose, axs[0])
barplot_latency(latency_tight, axs[1])
barplot_latency(deadline_loose, axs[2])
barplot_latency(deadline_tight, axs[3])
barplot_latency(QoE_loose, axs[4])
barplot_latency(QoE_tight, axs[5])


plot_legend()

plt.savefig('./overall_effectiveness.pdf', bbox_inches='tight')