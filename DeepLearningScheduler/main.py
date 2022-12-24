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
from validate_handlers import validate_handlers
from logging_config import logging_basic_setting
from control_signal import generate_signal, parse_signal, SignalCommand

class TaskStatus(Enum):
    Entry = 0
    Load = 1
    Ready = 2
    Running = 3
    Error = 4
    Exit = 5

async def handle_signaling(control_queue, base_time, config):
    """
    singaling response in child process
    handler the signals from controller to move itself to different status
    """
    handler_id, handler_name, handler_description, handler_priority, handler_dependencies, status = config
    logging.debug(f'handler signaling processing debug:{handler_id}, {handler_name}, {handler_dependencies}, {status}')
    while True:
        # 使用asyncio.sleep()挂起协程，让它不阻塞
        await asyncio.sleep(0)
        # 使用queue.get_nowait()检查queue是否有信号，如果有就立即返回，如果没有就抛出QueueEmpty异常
        try:
            signal_message = control_queue.get_nowait()
            # logging.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != handler_id):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            logging.info(f"[{handler_id}][{handler_name}] Received signal: [{signal_command}]")
            # depends on different signal to execute handlers
            if(SignalCommand[signal_command] == SignalCommand.PING):
                # return a time
                generate_signal(0, SignalCommand.PING, f"--time {time.time() - base_time}")
        except queue.Empty:
            continue


async def send_heart_ping(control_queue, handlers, relative_start_time):
    """
    A heart beat ping task, excuted by controller process.
    Send a ping with relative time to every handlers
    """
    basetime = relative_start_time
    while True:
        for handler in handlers:    
            # Generate the PING signal
            signal_heart = generate_signal(handler["id"], SignalCommand.PING, f"--time {math.floor(time.time()-basetime)}")
            # Send the PING signal to the control queue
            control_queue.put(signal_heart)
            # logging.debug(f'Send heart signal to subprocess {signal_heart}')


        # Wait for 1 second
        await asyncio.sleep(0.1)


async def main_process_signaling(control_queue, handlers, name2process):
    """
    signaling repsonse in controller process
    """
    # controller signal handle
    while True:
        await asyncio.sleep(0)
        try:
            signal_message = control_queue.get_nowait()
            # logging.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != 0):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            # 处理信号
            logging.debug(f"Received signal: {signal_message}")
        except queue.Empty:
            continue

def create_subprocess(handler_id, handler_name, handler_description, handler_priority, handler_dependencies, control_queue, base_time):
    """
    Function to run a single handler.
    This function is in a new process.
    """
    print(f"Running handler {handler_id}: {handler_name}")
    # import the handler module and init the class
    handler_file_name = f"handler{handler_id}"
    # handler_file_path = os.path.join('./handlers', f'{handler_file_name}.py') # generate dynamic path
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    handlers_dir = os.path.join(current_dir, 'handler')
    sys.path.append(handlers_dir)
    handler_module = importlib.import_module(f'{handler_file_name}')
    TaskConcreteClass = getattr(handler_module, handler_file_name)
    handler = TaskConcreteClass(handler_id, handler_name, handler_description, handler_priority, handler_dependencies)
    # init handler status
    status = TaskStatus.Entry
    logging.debug(f'Finish to create handler: {handler_name}')
    # start a coroutine to handle signal from the queue
    loop = asyncio.get_event_loop()
    handle_signaling_handler = loop.create_task(handle_signaling(control_queue, base_time, (handler_id, handler_name, handler_description, handler_priority, handler_dependencies, status)))
    try:
        loop.run_until_complete(handle_signaling_handler)
    except KeyboardInterrupt:
        print('[CLOSE] KeyboardInterrupt, close all handlers and loop')
    finally:
        loop.stop()
        loop.close()

    
    

def run_handlers(handlers, control_queue):
    """
    Function to run handlers concurrently.
    """
    # Create a list of processes
    processes = []
    # base time for all handlers and tasks
    base_time = time.time()
    name2process = defaultdict(None)
    for handler in handlers:
        handler_id = handler["id"]
        handler_name = handler["name"]
        handler_description = handler["description"]
        handler_priority = handler["priority"]
        handler_dependencies = handler["dependencies"]

        # Create a process for each handler
        process = Process(target=create_subprocess, name=handler_name, args=(handler_id, handler_name, handler_description, handler_priority, handler_dependencies, control_queue, base_time))
        processes.append(process)
        name2process[f'{handler_name}'] = process
    # Start all processes
    for process in processes:
        process.start()

    loop = asyncio.get_event_loop()
    daemon_signaling_handler = loop.create_task(main_process_signaling(control_queue, handlers, name2process))
    # main process send heartbeat signal to every subprocess per second
    hearping_handler = loop.create_task(send_heart_ping(control_queue, handlers, base_time))
    
    try:
        loop.run_until_complete(daemon_signaling_handler)
        loop.run_until_complete(hearping_handler)
    except KeyboardInterrupt:
        print('[CLOSE] KeyboardInterrupt, close all handlers and loop')
    finally:
        for process in processes:
            process.terminate()
        loop.stop()
        loop.close()

def parserHandler():
    """
    Function to parse the command line arguments.
    Validate the handler config file.
    Run the handlers.
    """
     # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--config", "-c", required=True, help="path of config file")
    parser.add_argument("--generate", "-g", required=False, help="path of handler folder to automatically infer the config file")
    args = parser.parse_args()

    # Load the handlers from the handler config file
    try:
        with open(args.config, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("Error: Invalid JSON file")
        return
    
    # Check if the config file has a handler list
    if "handler_list" not in config:
        print("Error: Missing `handler_list` in config file")
        return
    
    # Check if the handler list is a list
    if not isinstance(config["handler_list"], list):
        print("Error: `handler_list` must be a list")
        return
    
    handlers = config["handler_list"]
    
    # Validate the handlers
    try:
        validate_handlers(handlers)
    except ValueError as e:
        print(e)
    
    return handlers
    

if __name__ == "__main__":
    logging_basic_setting()
    handlers = parserHandler()
    # logging.debug(f'Parse config files to generate handlers: {handlers}')
    freeze_support()
    # Set the start method to spawn, The child process will only inherit those resources necessary to run the process object's run() method
    set_start_method('spawn')
    # Create a queue for control signals
    control_queue = Queue()

    # Start the handlers concurrently
    run_handlers(handlers, control_queue)