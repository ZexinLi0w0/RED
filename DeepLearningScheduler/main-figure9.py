import argparse
import json
import os, sys
import time, math
import queue
from multiprocessing import Process, Queue, freeze_support, set_start_method
import importlib
import asyncio
from collections import defaultdict
import logging

# self-defined modules
from validate_handlers import validate_handlers
from logging_config import logging_basic_setting
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from controller_signaling import send_heart_ping, controller_signaling, controller_signaling_SIMO
from handler_signaling import handle_signaling, handle_signaling_SIMO
from task_generator import generate_tasks, load_task_config, load_dag_config, generate_tasks_from_dag


if __name__ == "__main__":
    
    with open('./TaskConfigs/simo/agx_loose.json', "r") as f:
        config = json.load(f)
    
    dag_config = config["dag_list"]
    running_time_factor = 1
    if("RunningTimeFactor" in config):
        running_time_factor = config["RunningTimeFactor"]
    
    for running_time_factor in [1, 1.2, 1.4, 1.6, 1.8, 2]:
        config["RunningTimeFactor"] = running_time_factor
        with open(f'./TaskConfigs/simo/agx_loose{running_time_factor}.json', 'w') as f:
            json.dump(config, f)
        os.system(f'python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose{running_time_factor}.json" -a "baseline"')
        os.system(f"mv log.info.txt exp1/raw_data/agx_loose{running_time_factor}_baseline.txt")
        os.system(f'python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose{running_time_factor}.json" -a "feedback"')
        os.system(f"mv log.info.txt exp1/raw_data/agx_loose{running_time_factor}_progress_tracker.txt")
        os.system(f'python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose{running_time_factor}.json" -a "fine-grained"')
        os.system(f"mv log.info.txt exp1/raw_data/agx_loose{running_time_factor}_fine_grained.txt")
        os.system(f'python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose{running_time_factor}.json" -a "feedback-fine-grained"')
        os.system(f"mv log.info.txt exp1/raw_data/agx_loose{running_time_factor}_REDdrop.txt")
        os.system(f"rm ./TaskConfigs/simo/agx_loose{running_time_factor}.json")
        os.system(f"cat exp1/raw_data/agx_{running_time_factor}_baseline.txt | grep End | grep -oE ': [0-9]+.[0-9]+' | grep -oE '[0-9]+.[0-9]+' >> exp1/processed_data/agx_loose_{running_time_factor}_baseline.txt")
        os.system(f"cat exp1/raw_data/agx_{running_time_factor}_progress_tracker.txt | grep End | grep -oE ': [0-9]+.[0-9]+' | grep -oE '[0-9]+.[0-9]+' >> exp1/processed_data/agx_loose_{running_time_factor}_progress_tracker.txt")
        os.system(f"cat exp1/raw_data/agx_{running_time_factor}_fine_grained.txt | grep End | grep -oE ': [0-9]+.[0-9]+' | grep -oE '[0-9]+.[0-9]+' >> exp1/processed_data/agx_loose_{running_time_factor}_fine_grained.txt")
        os.system(f"cat exp1/raw_data/agx_{running_time_factor}_REDdrop.txt | grep End | grep -oE ': [0-9]+.[0-9]+' | grep -oE '[0-9]+.[0-9]+' >> exp1/processed_data/agx_loose_{running_time_factor}_REDdrop.txt")