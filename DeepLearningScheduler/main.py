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

def create_subprocess(control_queue, base_time, config=()):
    """
    Function to run a single handler.
    This function is in a new process.
    """
    handler_id, handler_name, handler_description, runargs = config
    logger = logging_basic_setting(handler_name)
    # logger.debug(f"Running handler {handler_id}: {handler_name}")
    # import the handler module and init the class
    handler_file_name = f"handler{handler_id}"
    # handler_file_path = os.path.join('./handlers', f'{handler_file_name}.py') # generate dynamic path
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    handlers_dir = os.path.join(current_dir, 'handler')
    sys.path.append(handlers_dir)
    handler_module = importlib.import_module(f'{handler_file_name}')
    TaskConcreteClass = getattr(handler_module, handler_file_name)
    instance = TaskConcreteClass(handler_id, handler_name, handler_description)
    
    # logger.debug(f'Already create handler class: {handler_name}, {instance.task_id}, {instance.task_priority}')
    
    # start a coroutine to handle signal from the queue
    loop = asyncio.get_event_loop()
    # config tuple
    main_task = loop.create_task(handle_signaling_SIMO(control_queue, base_time, config=config, logger=logger, instance=instance))
    try:
        loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        logger.info(f'[CLOSE] SubProcess [{handler_id}]{handler_name} KeyboardInterrupt, close all tasks and the loop')
    finally:
        loop.stop()
        loop.close()

def run_handlers(handlers, tasks_list, control_queue, logger, approach_module='baseline'):
    """
    Function to run handlers concurrently.
    """
    # Create a list of processes
    processes = []
    # base time for all handlers and tasks
    base_time = time.time()        
    for handler in handlers:
        handler_id = int(handler["id"])
        handler_name = handler["name"]
        handler_description = handler["description"]
        run_args = convert_args_to_dict(handler["run_args"] if "run_args" in handler else None)

        # Create a process for each handler
        config = (handler_id, handler_name, handler_description, run_args)        
        process = Process(target=create_subprocess, name=handler_name, args=(control_queue, base_time, config))
        processes.append(process)
    # Start all processes
    for process in processes:
        process.start()
    logger.info('[CTRL] All subprocesses started.')
    loop = asyncio.get_event_loop()
    # main process send heartbeat signal to every subprocess per second
    # heartping_handler = loop.create_task(send_heart_ping(control_queue, handlers, base_time=base_time, logger=logger))
    daemon_signaling_handler = loop.create_task(controller_signaling_SIMO(control_queue, handlers, tasks_list, approach_module=approach_module, logger=logger, base_time=base_time))
    
    try:
        # loop.run_until_complete(heartping_handler)
        loop.run_until_complete(daemon_signaling_handler)
    except KeyboardInterrupt:
        logger.info(f'[CLOSE] Controller Process KeyboardInterrupt, close all tasks and loop')
    finally:
        for process in processes:
            process.terminate()
        loop.stop()
        loop.close()

def parseArguments():
    """
    Function to parse the command line arguments.
    Validate the handler config file.
    Run the handlers and tasks loaded from config file.
    """
     # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--config", "-c", required=True, help="path of config file")
    parser.add_argument("--task", "-t", required=True, help="path of task config file")
    parser.add_argument("--approach", "-a", required=True, help="select approaches to adjust tasks: \n 1. baseline(do nothing), \n 2. feedback(according to the feedback of task execution to adjust next release time), \n 3. fine-grained(reconstruct dag in task generation), \n 4. feedback-fine-grained")
    parser.add_argument("--generate", "-g", required=False, help="path of handler folder to automatically infer the config file")

    args = parser.parse_args()

    # Load the handlers from the handler config file
    try:
        with open(args.config, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        raise Exception("Error: Invalid JSON file")
    
    # Check if the config file has a handler list
    if "handler_list" not in config:
        raise Exception("Error: Missing `handler_list` in config file")        
    
    # Check if the handler list is a list
    if not isinstance(config["handler_list"], list):
        raise Exception("Error: `handler_list` must be a list")

    approach_module = args.approach
    # check if the approach is valid
    if approach_module not in ["baseline", "feedback", "fine-grained", "feedback-fine-grained"]:
        raise Exception("Error: `approach` must be one of the following: baseline, feedback, fine-grained, feedback-fine-grained")
    
    handlers = config["handler_list"]
    
    # Validate the handlers
    try:
        validate_handlers(handlers)
    except ValueError as e:
        print(e)
    # for dag config
    task_config = load_dag_config(args.task)
    tasks_list = generate_tasks_from_dag(task_config)

    # task_config = load_task_config(args.task)
    # tasks_list = generate_tasks(task_config)
    
    return handlers, tasks_list, approach_module
    

if __name__ == "__main__":
    logger = logging_basic_setting()
    handlers, tasks_list, approach_module = parseArguments()
    # logging.debug(f'Parse config files to generate handlers: {handlers}')
    freeze_support()
    # Set the start method to spawn, The child process will only inherit those resources necessary to run the process object's run() method
    set_start_method('spawn')
    # Create a queue for control signals
    control_queue = Queue()

    # Start the handlers concurrently
    run_handlers(handlers, tasks_list, control_queue, logger, approach_module=approach_module)