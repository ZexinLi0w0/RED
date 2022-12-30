import asyncio, math, time
import queue
from collections import defaultdict
import logging

# self-defined modules
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from AbstractHandler import HandlerStatus


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

async def controller_signaling(control_queue, handlers, tasks_list, id2process, id2config, logger=logging, base_time=0):
    """
    signaling repsonse in controller process
    """
    allReady = defaultdict(bool)
    tasksGeneratedReady = False
    # the task queue, sorted by release time and priority
    TaskQueue = []
    # the start time of all tasks, all release time and deadline are relative to this time
    TaskStartTime = base_time
    # controller maintain a handler status dict
    handler_status = defaultdict(None)
    # statistics map of tasks Map<TaskId, TaskFinishedObject>
    task_statistics = defaultdict(dict)
    # send signal to handlers to start
    for handler in handlers:
        signal_message = generate_signal(handler["id"], SignalCommand.LOADDATA)
        control_queue.put(signal_message)
        handler_status[handler["id"]] = HandlerStatus.Load
        allReady[handler["id"]] = False
    # controller signal response loop
    while True: 
        # when all handlers are ready and tasks are not generated, generate tasks
        if(all(allReady.values()) and not tasksGeneratedReady):
            TaskStartTime = time.time()
            for task in tasks_list:
                handler_id = task["HandlerId"]
                taskid = f"--taskid {task['TaskId']}"
                release_time = f"--release_time {task['ReleaseTime']}"
                deadline = f"--deadline {task['Deadline']}"
                relative_time = f"--relative_time {TaskStartTime}" # relative start time of all tasks
                signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid)
                delay_signal = (signal_message, task)
                TaskQueue.append(delay_signal)
                # record the task object for statistics
                task_statistics[task["TaskId"]] = {
                    "release_time": task["ReleaseTime"],
                    "deadline": task["Deadline"],
                    "priority": task["Priority"],
                    "dependency": task["Dependencies"]
                }
            # sort the tasks by release time and priority
            TaskQueue.sort(key=lambda x: (x[1]["ReleaseTime"], -x[1]["Priority"]))
            tasksGeneratedReady = True
            logger.info(f"[CTRL] Tasks generated, start time: {TaskStartTime}")
        # await asyncio.sleep(0)
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
            # when received a ping signal from handler, which means handler changed their status
            if(SignalCommand[signal_command] == SignalCommand.PING):
                if(HandlerStatus[args_dict["status"]] == HandlerStatus.Load):
                    # send a signal to subprocess to ready(ready to run)
                    handler_status[args_dict["source"]] = HandlerStatus.Ready
                    signal_message = generate_signal(args_dict["source"], SignalCommand.READY)
                    control_queue.put(signal_message)
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Ready):
                    # Ready means the handler is ready to receive tasks
                    handler_id = args_dict["source"]
                    # mark this handler as ready
                    allReady[handler_id] = True
            # when handlers finished one task and deliver the result
            elif(SignalCommand[signal_command] == SignalCommand.DELIVERY):
                # logger.debug(f"Received delivery signal: {signal_message}")
                handler_id = args_dict["source"]
                # set the handler status to ready
                handler_status[handler_id] = HandlerStatus.Ready
                task_statistics[args_dict["taskid"]]["res"] = args_dict["output"]
                task_statistics[args_dict["taskid"]]["start_time"] = args_dict["start_time"]
                task_statistics[args_dict["taskid"]]["end_time"] = args_dict["end_time"]
                logger.info(f"[CTRL] Task {args_dict['taskid']} finished, start time: {args_dict['start_time']}, end time: {args_dict['end_time']}")
            
            # Distribute the tasks in TaskQueue
            if(tasksGeneratedReady):
                putback = []
                while(len(TaskQueue) > 0):
                    item = TaskQueue.pop(0)
                    # distribute tasks
                    signal_message, task = item
                    now = time.time()
                    release_time = task["ReleaseTime"]
                    handler_id = task["HandlerId"]
                    # check if the task is ready to release, and the handler is ready to receive
                    if(now - TaskStartTime >= release_time and handler_status[handler_id] == HandlerStatus.Ready):
                        # send the signal to the handler
                        control_queue.put(signal_message)
                        logger.debug(f"[CTRL] Send task signal {signal_message} on {now-TaskStartTime} s")
                    else:
                        # put it back
                        putback.append(item)
                    if(now - TaskStartTime < task["ReleaseTime"]):
                        # the following tasks are not ready to release
                        break
                if(len(putback) > 0):
                    TaskQueue = putback + TaskQueue
        except queue.Empty:
            continue




def circle_status(control_queue, signal_command, signal_args, id2config, base_time=0, logger=logging):
    args_dict = convert_args_to_dict(signal_args)
    # logger.debug(f"[CTRL] Received signal: {signal_message},\n Parse args_dict: {args_dict}")
    if(SignalCommand[signal_command] == SignalCommand.PING):
        if(HandlerStatus[args_dict["status"]] == HandlerStatus.Entry):
            # send a signal to subprocess to load data
            signal_message = generate_signal(args_dict["source"], SignalCommand.LOADDATA)
            control_queue.put(signal_message)
        elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Load):
            # send a signal to subprocess to ready(ready to run)
            signal_message = generate_signal(args_dict["source"], SignalCommand.READY)
            control_queue.put(signal_message)
        elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Ready):
            # send a signal to subprocess to run
            # for different subprocess, we can pass constrain as arguments
            signal_message = generate_signal(args_dict["source"], SignalCommand.RUN)
            control_queue.put(signal_message)
        elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Running):
            # send a signal to subprocess to ready
            config = id2config[int(args_dict["source"])]
            handler_id, handler_name, handler_description, runargs = config
            if("release-time" in runargs):
                # wait until delay to release time
                if(float(runargs["release-time"]) > time.time() - base_time):
                    return
            logger.info(f'[CTRL] Received task[{args_dict["source"]}] running output: {signal_message}')
            signal_message = generate_signal(args_dict["source"], SignalCommand.READY)
            control_queue.put(signal_message)