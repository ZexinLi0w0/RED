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
from enum import Enum

# self-defined moduls
from validate_tasks import validate_tasks
from logging_config import logging_basic_setting
from control_signal import generate_signal, parse_signal, SignalCommand

class TaskStatus(Enum):
    Entry = 0
    Load = 1
    Ready = 2
    Running = 3
    Error = 4
    Exit = 5

async def handle_signaling(control_queue, task_id, task_name, task_description, task_priority, task_dependencies):
    while True:
        # 使用asyncio.sleep()挂起协程，让它不阻塞
        await asyncio.sleep(0)
        # 使用queue.get_nowait()检查queue是否有信号，如果有就立即返回，如果没有就抛出QueueEmpty异常
        try:
            signal_message = control_queue.get_nowait()
            # logging.debug(f"Received signal: {signal_message}")
            # only handle the signal with their taskid
            signal_taskid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_taskid != f"{task_id}"):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            logging.info(f"[{task_id}][{task_name}] Received signal: [{signal_command}]")
            # depends on different signal to execute tasks

        except queue.Empty:
            continue


async def send_heart_ping(control_queue, task):
    basetime = time.time()
    while True:
        for task in tasks:    
            # Generate the PING signal
            signal_heart = generate_signal(task["id"], SignalCommand.PING, f"--time {math.floor(time.time()-basetime)}")
            # Send the PING signal to the control queue
            control_queue.put(signal_heart)


        # Wait for 1 second
        await asyncio.sleep(1)


async def main_process_signaling(control_queue, tasks, name2process):
    # controller signal handle
    while True:
        await asyncio.sleep(0)
        try:
            signal = control_queue.get_nowait()
            if(not signal):
                return
            # 处理信号
            print(f"Received signal: {signal}")
        except queue.Empty:
            continue

def create_subprocess(task_id, task_name, task_description, task_priority, task_dependencies, task_command, control_queue):
    """
    Function to run a single task.
    This function is in a new process.
    """
    print(f"Running task {task_id}: {task_name}")
    # Run the task command
    task_file_name = f"task{task_id}"
    # task_file_path = os.path.join('./tasks', f'{task_file_name}.py') # generate dynamic path
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    tasks_dir = os.path.join(current_dir, 'tasks')
    sys.path.append(tasks_dir)
    task_module = importlib.import_module(f'{task_file_name}')
    TaskConcreteClass = getattr(task_module, task_file_name)
    task = TaskConcreteClass(task_id, task_name, task_description, task_priority, task_dependencies, task_command, TaskStatus.Entry)
    
    # start a coroutine to handle signal from the queue
    loop = asyncio.get_event_loop()
    handle_signaling_task = loop.create_task(handle_signaling(control_queue, task_id, task_name, task_description, task_priority, task_dependencies))
    try:
        loop.run_until_complete(handle_signaling_task)
    except KeyboardInterrupt:
        print('[CLOSE] KeyboardInterrupt, close all tasks and loop')
    finally:
        loop.stop()
        loop.close()

    
    

def run_tasks(tasks, control_queue):
    """
    Function to run tasks concurrently.
    """
    # Create a list of processes
    processes = []
    name2process = defaultdict(None)
    for task in tasks:
        task_id = task["id"]
        task_name = task["name"]
        task_description = task["description"]
        task_priority = task["priority"]
        task_dependencies = task["dependencies"]
        task_command = task["run"]

        # Create a process for each task
        process = Process(target=create_subprocess, name=task_name, args=(task_id, task_name, task_description, task_priority, task_dependencies, task_command, control_queue))
        processes.append(process)
        name2process[f'{task_name}'] = process
    # Start all processes
    for process in processes:
        process.start()

    loop = asyncio.get_event_loop()
    daemon_signaling_handler = loop.create_task(main_process_signaling(control_queue, tasks, name2process))
    # main process send heartbeat signal to every subprocess per second
    hearping_task = loop.create_task(send_heart_ping(control_queue, tasks))
    try:
        loop.run_until_complete(daemon_signaling_handler)
        loop.run_until_complete(hearping_task)
    except KeyboardInterrupt:
        print('[CLOSE] KeyboardInterrupt, close all tasks and loop')
    finally:
        for process in processes:
            process.terminate()
        loop.stop()
        loop.close()

def parserHandler():
    """
    Function to parse the command line arguments.
    Validate the task config file.
    Run the tasks.
    """
     # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--input", "-i", required=True, help="path of input task config file")
    parser.add_argument("--generate", "-g", required=False, help="path of tasks folder to automatically infer the task config file")
    args = parser.parse_args()

    # Load the tasks from the task config file
    try:
        with open(args.input, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("Error: Invalid JSON file")
        return
    
    # Check if the config file has a task list
    if "tasklist" not in config:
        print("Error: Missing `tasklist` in config file")
        return
    
    # Check if the task list is a list
    if not isinstance(config["tasklist"], list):
        print("Error: `tasklist` must be a list")
        return
    
    tasks = config["tasklist"]
    
    # Validate the tasks
    try:
        validate_tasks(tasks)
    except ValueError as e:
        print(e)
    
    return tasks
    

if __name__ == "__main__":
    logging_basic_setting()
    tasks = parserHandler()
    freeze_support()
    # Set the start method to spawn, The child process will only inherit those resources necessary to run the process object's run() method
    set_start_method('spawn')
    # Create a queue for control signals
    control_queue = Queue()

    # Start the tasks concurrently
    run_tasks(tasks, control_queue)