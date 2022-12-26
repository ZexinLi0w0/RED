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
from AbstractHandler import HandlerStatus

async def handle_signaling(control_queue, base_time, config, logger=logging, instance=None):
    """
    singaling response in child process
    handler the signals from controller to move itself to different status
    """
    handler_id, handler_name, handler_description, handler_priority, handler_dependencies = config
    if(instance is None):
        logger.critical(f"Can not create a signaling handler without task instance in task [{handler_id}]{handler_name}")
        return
    STATUS = HandlerStatus.Entry
    logger.debug(f'handler signaling processing debug:{handler_id}, {handler_name}, {handler_description}, {handler_priority}, {handler_dependencies}, {STATUS}')
    while True:
        # 使用asyncio.sleep()挂起协程，让它不阻塞
        # await asyncio.sleep(0)
        # 使用queue.get_nowait()检查queue是否有信号，如果有就立即返回，如果没有就抛出queue.Empty异常
        try:
            signal_message = control_queue.get_nowait()
            # logging.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != handler_id):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            # logger.info(f"[{handler_id}][{handler_name}] Received signal: [{signal_command}]")
            # depends on different signal to execute handlers
            if(SignalCommand[signal_command] == SignalCommand.PING):
                # return a time
                reply_time = f"--time {time.time() - base_time}"
                # use this handler_id as unique identity
                reply_source = f"--source {handler_id}"
                # for enum value, must send it's value so that the receiver can match it.
                reply_status = f"--status {STATUS.value}"
                # only in status entry, reply heart ping
                if(STATUS == HandlerStatus.Entry):
                    signal_message = generate_signal(0, SignalCommand.PING, reply_time, reply_source, reply_status)
                    control_queue.put(signal_message)
                continue
            elif(SignalCommand[signal_command] == SignalCommand.LOADDATA):
                # skip repeat signal while already in execution
                if(STATUS == HandlerStatus.Load):
                    continue
                loop = asyncio.get_event_loop()
                start_time = time.time() - base_time
                # load data until finished
                await loop.create_task(instance.load_data())
                STATUS = HandlerStatus.Load
                reply_start_time = f"--start_time {start_time}"
                reply_end_time = f"--end_time {time.time() - base_time}"
                reply_source = f"--source {handler_id}" # use this handler_id as unique identity
                reply_status = f"--status {STATUS.value}" # for enum value, must send it's value so that the receiver can match it.
                signal_message = generate_signal(0, SignalCommand.PING, reply_source, reply_status, reply_start_time, reply_end_time)
                control_queue.put(signal_message)
                continue
            elif(SignalCommand[signal_command] == SignalCommand.READY):
                # skip repeat signal while already in execution
                if(STATUS == HandlerStatus.Ready):
                    continue
                start_time = time.time() - base_time
                # set to ready
                instance.ready()
                STATUS = HandlerStatus.Ready
                reply_start_time = f"--start_time {start_time}"
                reply_end_time = f"--end_time {time.time() - base_time}"
                reply_source = f"--source {handler_id}" # use this handler_id as unique identity
                reply_status = f"--status {STATUS.value}" # for enum value, must send it's value so that the receiver can match it.
                signal_message = generate_signal(0, SignalCommand.PING, reply_source, reply_status, reply_start_time, reply_end_time)
                control_queue.put(signal_message)
                continue
            elif(SignalCommand[signal_command] == SignalCommand.RUN):
                # skip repeat signal while already in execution
                if(STATUS == HandlerStatus.Running):
                    continue
                loop = asyncio.get_event_loop()
                start_time = time.time() - base_time
                # load data until finished
                output = await loop.create_task(instance.run())
                STATUS = HandlerStatus.Running
                reply_start_time = f"--start_time {start_time}"
                reply_end_time = f"--end_time {time.time() - base_time}"
                reply_source = f"--source {handler_id}" # use this handler_id as unique identity
                reply_status = f"--status {STATUS.value}" # for enum value, must send it's value so that the receiver can match it.
                reply_output = f"--output {output}"
                signal_message = generate_signal(0, SignalCommand.PING, reply_source, reply_status, reply_output, reply_start_time, reply_end_time)
                control_queue.put(signal_message)
                continue
        except queue.Empty:
            continue

async def send_heart_ping(control_queue, handlers, relative_start_time, logger=logging):
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
            logger.debug(f'Send heart signal to subprocess {signal_heart}')

        # 6ms overhead

        # Wait for 1 second
        await asyncio.sleep(0.1)


async def main_process_signaling(control_queue, handlers, name2process, id2process, logger=logging):
    """
    signaling repsonse in controller process
    """
    # controller signal handle
    while True:
        await asyncio.sleep(0)
        try:
            signal_message = control_queue.get_nowait()
            # logger.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != 0):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            # 处理信号
            args_dict = convert_args_to_dict(signal_args)
            # logger.debug(f"[CTRL] Received signal: {signal_message},\n Parse args_dict: {args_dict}")
            if(SignalCommand[signal_command] == SignalCommand.PING):
                if(HandlerStatus[args_dict["status"]] == HandlerStatus.Entry):
                    # send a signal to subprocess to load data
                    signal_message = generate_signal(args_dict["source"], SignalCommand.LOADDATA)
                    control_queue.put(signal_message)
                    continue
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Load):
                    # send a signal to subprocess to ready(ready to run)
                    signal_message = generate_signal(args_dict["source"], SignalCommand.READY)
                    control_queue.put(signal_message)
                    continue
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Ready):
                    # send a signal to subprocess to run
                    # for different subprocess, we can pass constrain as arguments
                    signal_message = generate_signal(args_dict["source"], SignalCommand.RUN)
                    control_queue.put(signal_message)
                    continue
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Running):
                    # send a signal to subprocess to ready
                    logger.info(f'[CTRL] Received task[{args_dict["source"]}] running output: {signal_message}')
                    signal_message = generate_signal(args_dict["source"], SignalCommand.READY)
                    control_queue.put(signal_message)
                    continue

        except queue.Empty:
            continue

def create_subprocess(handler_id, handler_name, handler_description, handler_priority, handler_dependencies, control_queue, base_time):
    """
    Function to run a single handler.
    This function is in a new process.
    """
    logger = logging_basic_setting(handler_name)
    logger.debug(f"Running handler {handler_id}: {handler_name}")
    # import the handler module and init the class
    handler_file_name = f"handler{handler_id}"
    # handler_file_path = os.path.join('./handlers', f'{handler_file_name}.py') # generate dynamic path
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    handlers_dir = os.path.join(current_dir, 'handler')
    sys.path.append(handlers_dir)
    handler_module = importlib.import_module(f'{handler_file_name}')
    TaskConcreteClass = getattr(handler_module, handler_file_name)
    instance = TaskConcreteClass(handler_id, handler_name, handler_description, handler_priority, handler_dependencies)
    
    logger.debug(f'Already create handler class: {handler_name}, {instance.task_id}, {instance.task_priority}')
    
    # start a coroutine to handle signal from the queue
    loop = asyncio.get_event_loop()
    # config tuple
    config = (handler_id, handler_name, handler_description, handler_priority, handler_dependencies)
    main_task = loop.create_task(handle_signaling(control_queue, base_time, config, logger=logger, instance=instance))
    try:
        loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        logger.info(f'[CLOSE] SubProcess [{handler_id}]{handler_name} KeyboardInterrupt, close all tasks and the loop')
    finally:
        loop.stop()
        loop.close()

def run_handlers(handlers, control_queue, logger):
    """
    Function to run handlers concurrently.
    """
    # Create a list of processes
    processes = []
    # base time for all handlers and tasks
    base_time = time.time()
    name2process = defaultdict(None)
    id2process = defaultdict(None)
    for handler in handlers:
        handler_id = handler["id"]
        handler_name = handler["name"]
        handler_description = handler["description"]
        handler_priority = handler["priority"]
        handler_dependencies = handler["dependencies"]

        # Create a process for each handler
        process = Process(target=create_subprocess, name=handler_name, args=(handler_id, handler_name, handler_description, handler_priority, handler_dependencies, control_queue, base_time))
        processes.append(process)
        name2process[handler_name] = process
        id2process[handler_id] = process
    # Start all processes
    for process in processes:
        process.start()
    logger.info('[CTRL] All subprocesses started.')
    loop = asyncio.get_event_loop()
    daemon_signaling_handler = loop.create_task(main_process_signaling(control_queue, handlers, name2process, id2process, logger=logger))
    # main process send heartbeat signal to every subprocess per second
    hearping_handler = loop.create_task(send_heart_ping(control_queue, handlers, base_time, logger=logger))
    
    try:
        loop.run_until_complete(daemon_signaling_handler)
        loop.run_until_complete(hearping_handler)
    except KeyboardInterrupt:
        logger.info(f'[CLOSE] Controller Process KeyboardInterrupt, close all tasks and loop')
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
    logger = logging_basic_setting()
    handlers = parserHandler()
    # logging.debug(f'Parse config files to generate handlers: {handlers}')
    freeze_support()
    # Set the start method to spawn, The child process will only inherit those resources necessary to run the process object's run() method
    set_start_method('spawn')
    # Create a queue for control signals
    control_queue = Queue()

    # Start the handlers concurrently
    run_handlers(handlers, control_queue, logger)