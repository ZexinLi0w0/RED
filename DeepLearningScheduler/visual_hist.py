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
    # methods = ['EDF', 'RED-FG', 'RED-IDA', 'RED']
    # custom_colors = ['white', 'lightgray', 'darkgray', 'black']

    methods = ['EDF', 'RED']
    color_list = ['#FFE87C', '#ADD8E6']

    # hatches = ['/', 'x', '\\', '+']  # Corrected hatches
    legend_patches = [
        mpatches.Patch(facecolor=color_list[i],
                       # hatch=hatches[i],
                       edgecolor='black',
                       label=device)
        for i, device in enumerate(methods)
    ]
    fig.legend(handles=legend_patches, loc='upper center', ncol=4, fontsize=fontsize, bbox_to_anchor=(0.5, 1.03),
               edgecolor='black')

def histogram_latency(source_data, ax):
    bin_width = 0.05
    min_value = 0
    max_value = 10
    bin_edges = np.arange(min_value, max_value + bin_width, bin_width)



    # EDF = np.array(source_data['EDF'])
    # RED_FG = np.array(source_data['RED-FG'])
    # RED_IDA = np.array(source_data['RED-IDA'])
    # RED = np.array(source_data['RED'])

    np.random.seed(42)  # For reproducibility
    EDF = np.random.normal(loc=5, scale=1.5, size=10000)  # loc is the mean, scale is the standard deviation
    RED = np.random.normal(loc=7, scale=2.0, size=10000)

    # all_data = [EDF, RED_FG, RED_IDA, RED]
    all_data = [EDF, RED]
    approaches = ['EDF', 'RED-FG', 'RED-IDA', 'RED']

    import ChromaPalette as cp

    # color_list = cp.chroma_palette.color_palette("BlueGradient", 4)


    # color_list = ['#000000', '#FFFFFF']
    color_list = ['#FFE87C', '#ADD8E6']

    for idx, data in enumerate(all_data):
        ax.hist(data, bins=bin_edges, label=approaches[idx], color=color_list[idx], density=True, alpha=0.5)

    # ax.set_xticks([])
    ax.tick_params(axis='y', labelsize=fontsize)
    ax.tick_params(axis='x', labelsize=fontsize)
    ax.set_ylabel('{}'.format(source_data['metrics']), fontsize=fontsize)
    ax.set_title('{}'.format(source_data['title']), fontsize=fontsize)

latency_nano = {
    'EDF': [11.317, 9.458, 8.068, 3.603, 11.317, 9.458, 8.068, 3.603, 11.317, 9.458, 8.068, 3.603, 11.317, 9.458, 8.068, 3.603, 11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "Relative Frequency",
    'title': "Nano",
}

latency_tx2 = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "Relative Frequency",
    'title': "TX2",
}

latency_xavier = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "Relative Frequency",
    'title': "Xavier",
}

latency_orin = {
    'EDF': [11.317, 9.458, 8.068, 3.603],
    'RED-FG': [11.307, 8.831, 7.287, 3.461],
    'RED-IDA': [10.861, 9.675, 8.114, 3.693],
    'RED': [9.843, 8.143, 5.606, 2.745],
    'metrics': "Relative Frequency",
    'title': "Orin",
}

figsize = (17, 6)
fig, axs = plt.subplots(2, 2, figsize=figsize)
plt.subplots_adjust(hspace=0.4, wspace=0.3)  # adjust the space between subplots

histogram_latency(latency_nano, axs[0,0])
histogram_latency(latency_tx2, axs[0,1])
histogram_latency(latency_xavier, axs[1,0])
histogram_latency(latency_orin, axs[1,1])

plot_legend()

plt.savefig('./hist.pdf', bbox_inches='tight')