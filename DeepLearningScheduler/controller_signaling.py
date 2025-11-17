import asyncio, math, time
import queue
from collections import defaultdict
import logging
import datetime
import pickle

# self-defined modules
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from visual_scripts.visual_task import statistics_compution, task_scatter
from AbstractHandler import HandlerStatus
from task_scheduler import TaskSchedule


async def send_heart_ping(control_queue, handlers, logger=logging, base_time = 0):
    """
    A heart beat ping task, excuted by controller process.
    Send a ping with relative time to every handlers
    """
    while True:
        try:
            for handler in handlers:    
                # Generate the PING signal
                signal_heart = generate_signal(handler["id"], SignalCommand.PING, f"--time {math.floor(time.time()-base_time)}")
                # Send the PING signal to the control queue
                control_queue.put(signal_heart)

            # 6ms overhead

            # Wait for 1 second
            await asyncio.sleep(1/60)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"[CTRL] Error in heart ping: {e}")
            continue

async def controller_signaling(control_queue, handlers, tasks_list, logger=logging, base_time=0, approach_module='baseline'):
    """
    signaling repsonse in controller process
    """
    allReady = defaultdict(bool)
    warmup = defaultdict(int)
    tasksGeneratedReady = False
    # controller maintain a handler status dict
    handler_status = defaultdict(None)

    # send signal to handlers to start
    for handler in handlers:
        signal_message = generate_signal(handler["id"], SignalCommand.LOADDATA)
        control_queue.put(signal_message)
        handler_status[handler["id"]] = HandlerStatus.Load
        allReady[handler["id"]] = False
        warmup[handler["id"]] = 0
    
    # register task scheduler with edf scheduler
    task_scheduler = TaskSchedule(tasks_list, handler_status=handler_status, control_queue=control_queue, scheduler='edf', logger=logger)
    # controller signal response loop
    while True: 
        # avoid to busy loop
        await asyncio.sleep(0)
        # when all handlers are ready and tasks are not generated, generate tasks
        if(not tasksGeneratedReady and all(allReady.values())):
            task_scheduler.generate_task_list()
            tasksGeneratedReady = True
            logger.info(f"[CTRL] Tasks generated, offline scheduler: {task_scheduler.scheduler_name}, start time: {task_scheduler.TaskStartTime}, finished time: {time.time()}")
        # Distribute the tasks in TaskQueue
        elif(tasksGeneratedReady):
            continue_distribution = task_scheduler.distribute_tasks()
            if(not continue_distribution):
                break
        # read signals from queue and handle it
        try:
            signal_message = control_queue.get_nowait()
            # logger.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != 0):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            args_dict = convert_args_to_dict(signal_args)
            handler_id = int(args_dict["source"])
            # when received a ping signal from handler, which means handler changed their status
            if(SignalCommand[signal_command] == SignalCommand.PING):
                if(HandlerStatus[args_dict["status"]] == HandlerStatus.Load):
                    # send a signal to subprocess to ready(ready to run)
                    task_scheduler.handler_status[handler_id] = HandlerStatus.Ready
                    signal_message = generate_signal(handler_id, SignalCommand.READY)
                    control_queue.put(signal_message)
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Ready):
                    # before all handlers are ready, we need to warmup the handlers
                    if(not all(allReady.values())):
                        if("warmup" in args_dict):
                            warmup[handler_id] += 1
                            if(warmup[handler_id] >= 20):
                                allReady[handler_id] = True
                            else:
                                # send a signal to warmup
                                taskid = f"--taskid warmup"
                                signal_message = generate_signal(handler_id, SignalCommand.RUN, taskid, "--warmup true")
                                control_queue.put(signal_message)
                        else:
                            # send a signal to warmup
                            taskid = f"--taskid warmup"
                            signal_message = generate_signal(handler_id, SignalCommand.RUN, taskid, "--warmup true")
                            control_queue.put(signal_message)
                    # logger.debug(f"[CTRL] Handler {handler_id} is ready, is allready: {all(allReady.values())}, {allReady.values()}")
            # when handlers finished one task and deliver the result
            elif(SignalCommand[signal_command] == SignalCommand.DELIVERY):
                # logger.debug(f"Received delivery signal: {signal_message}")
                # set the handler status to ready
                task_scheduler.handler_status[handler_id] = HandlerStatus.Ready
                taskid = args_dict["taskid"]
                if(args_dict["output"] == "success"):
                    # add output for dependency consuming
                    task_scheduler.add_task_output(1, handler_id)
                task_scheduler.add_task_statistics(taskid, args_dict["output"], args_dict["start_time"], args_dict["end_time"])
                logger.info(f"[CTRL] Task {args_dict['taskid']} finished, status: {args_dict['output']}, start time: {args_dict['start_time']}, over time: {args_dict['end_time']}")
            
        except queue.Empty:
            continue

async def controller_signaling_SIMO(control_queue, handlers, tasks_list, approach_module='baseline', logger=logging, base_time=0, task_filename='task-config', burst_config=None, burst_task_ratio=0):
    """
    SIMO Baseline handler
    """
    allReady = defaultdict(bool)
    warmup = defaultdict(int)
    tasksGeneratedReady = False
    # controller maintain a handler status dict
    handler_status = defaultdict(None)

    # send signal to handlers to start
    for handler in handlers:
        signal_message = generate_signal(handler["id"], SignalCommand.LOADDATA)
        control_queue.put(signal_message)
        handler_status[handler["id"]] = HandlerStatus.Load
        allReady[handler["id"]] = False
        warmup[handler["id"]] = 0
    
    # register task scheduler with edf scheduler
    burst_enabled = burst_config is not None and burst_config.get('burst_enabled', False)
    task_scheduler = TaskSchedule(
        tasks_list, 
        handler_status=handler_status, 
        control_queue=control_queue, 
        scheduler='edf', 
        logger=logger, 
        approach_module=approach_module, 
        task_filename=task_filename,
        burst_enabled=burst_enabled,
        burst_config=burst_config,
        burst_task_ratio=burst_task_ratio
    )
    # controller signal response loop
    while True: 
        # avoid to busy loop
        await asyncio.sleep(0)
        # when all handlers are ready and tasks are not generated, generate tasks
        if(not tasksGeneratedReady and all(allReady.values())):
            task_scheduler.generate_task_list()
            tasksGeneratedReady = True
            logger.info(f"[CTRL] Tasks generated, offline scheduler: {task_scheduler.scheduler_name}, start time: {task_scheduler.TaskStartTime}, finished time: {time.time()}")
        # Distribute the tasks in TaskQueue
        elif(tasksGeneratedReady):
            continue_distribution = task_scheduler.distribute_tasks()
            if(not continue_distribution):
                break
        # read signals from queue and handle it
        try:
            signal_message = control_queue.get_nowait()
            # logger.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != 0):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            args_dict = convert_args_to_dict(signal_args)
            handler_id = int(args_dict["source"])
            # when received a ping signal from handler, which means handler changed their status
            if(SignalCommand[signal_command] == SignalCommand.PING):
                if(HandlerStatus[args_dict["status"]] == HandlerStatus.Load):
                    # send a signal to subprocess to ready(ready to run)
                    task_scheduler.handler_status[handler_id] = HandlerStatus.Ready
                    signal_message = generate_signal(handler_id, SignalCommand.READY)
                    control_queue.put(signal_message)
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Ready):
                    # before all handlers are ready, we need to warmup the handlers
                    if(not all(allReady.values())):
                        if("warmup" in args_dict):
                            warmup[handler_id] += 1
                            if(warmup[handler_id] >= 20):
                                allReady[handler_id] = True
                            else:
                                # send a signal to warmup
                                taskid = f"--taskid warmup"
                                signal_message = generate_signal(handler_id, SignalCommand.RUN, taskid, "--warmup true")
                                control_queue.put(signal_message)
                        else:
                            # send a signal to warmup
                            taskid = f"--taskid warmup"
                            signal_message = generate_signal(handler_id, SignalCommand.RUN, taskid, "--warmup true")
                            control_queue.put(signal_message)
                    # logger.debug(f"[CTRL] Handler {handler_id} is ready, is allready: {all(allReady.values())}, {allReady.values()}")
            # when handlers finished one task and deliver the result
            elif(SignalCommand[signal_command] == SignalCommand.DELIVERY):
                # logger.debug(f"Received delivery signal: {signal_message}")
                # set the handler status to ready
                task_scheduler.handler_status[handler_id] = HandlerStatus.Ready                
                taskid = args_dict["taskid"]
                simo_args = args_dict["simo_args"]
                end_time = float(args_dict["end_time"])
                dag_period = int(args_dict["dag_period"])
                # convert string simo args '[1,2]' to list
                task_types = [int(i) for i in simo_args.strip('[').strip(']').split(',')]
                if(approach_module == 'feedback' or approach_module == 'feedback-fine-grained'):
                    # adjust the release time of next task immediately
                    task_scheduler.feedback_adjust(end_time)
                # missing deadline or success will contribute the output, only skipped won't contribute
                if(args_dict["output"] == "success" or args_dict["output"] == "failure"):
                    # add output for dependency consuming
                    for task_type in task_types:
                        task_scheduler.add_task_output(dag_period, task_type)
                else:
                    # skipped task will not contribute the output, will cause discard on the following tasks which have dependency on it
                    for task_type in task_types:
                        task_scheduler.skipped_dependent_tasks(taskid, dag_period, task_type, now_time=end_time)
                # report finsihed task to task scheduler
                task_scheduler.finished_task(taskid, args_dict["output"], args_dict["start_time"], args_dict["end_time"])
                logger.info(f"[CTRL] Task {args_dict['taskid']} finished, status: {args_dict['output']}, start time: {args_dict['start_time']}, taskover time: {args_dict['end_time']}")
            
        except queue.Empty:
            continue
