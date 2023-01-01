import asyncio, math, time
import queue
from collections import defaultdict
import logging
import datetime
import pickle

# self-defined modules
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from visual_task import statistics_compution, task_scatter
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
    warmup = defaultdict(int)
    tasksGeneratedReady = False
    # the task queue, sorted by release time and priority
    TaskQueue = []
    # the start time of all tasks, all release time and deadline are relative to this time
    TaskStartTime = base_time
    # controller maintain a handler status dict
    handler_status = defaultdict(None)
    # statistics map of tasks Map<TaskId, TaskFinishedObject>
    task_statistics = defaultdict(dict)

    # dependency map of tasks Map<TaskId, Number of TaskOutput>
    task_dependency = defaultdict(int)

    # send signal to handlers to start
    for handler in handlers:
        signal_message = generate_signal(handler["id"], SignalCommand.LOADDATA)
        control_queue.put(signal_message)
        handler_status[handler["id"]] = HandlerStatus.Load
        allReady[handler["id"]] = False
        warmup[handler["id"]] = 0
    # controller signal response loop
    while True: 
        # avoid to busy loop
        await asyncio.sleep(0)
        # when all handlers are ready and tasks are not generated, generate tasks
        if(not tasksGeneratedReady and all(allReady.values())):
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
                    "handler_id":  task["HandlerId"],
                    "taskid": task["TaskId"],
                    "release_time": task["ReleaseTime"],
                    "deadline": task["Deadline"],
                    "priority": task["Priority"],
                    "dependency": task["Dependencies"]
                }
            # sort the tasks by release time and priority
            TaskQueue.sort(key=lambda x: (x[1]["ReleaseTime"], -x[1]["Priority"]))
            tasksGeneratedReady = True
            logger.info(f"[CTRL] Tasks generated, start time: {TaskStartTime}, finished time: {time.time()}")
        # Distribute the tasks in TaskQueue
        elif(tasksGeneratedReady):
            putback = []
            while(len(TaskQueue) > 0):
                item = TaskQueue.pop(0)
                # distribute tasks
                signal_message, task = item
                now = time.time()
                release_time = task["ReleaseTime"]
                handler_id = int(task["HandlerId"])
                # check if the task is ready to release, and the handler is ready to receive
                if(now - TaskStartTime >= release_time and handler_status[handler_id] == HandlerStatus.Ready and all(task_dependency[i] >= 1 for i in task["Dependencies"])):
                    # send the signal to the handler
                    # cosume the dependency output
                    for i in task["Dependencies"]:
                        task_dependency[i] -= 1
                    control_queue.put(signal_message)
                    logger.debug(f"[CTRL] Send task signal {signal_message} on {now-TaskStartTime} s")
                else:
                    if((now - TaskStartTime) >= task["Deadline"] and handler_status[handler_id] == HandlerStatus.Ready):
                        # directly send this task
                        control_queue.put(signal_message)
                        continue
                    # logger.debug(f"[CTRL] Put task back {signal_message} on {now-TaskStartTime} s")
                    # put it back
                    putback.append(item)
                # the following tasks are not ready to release
                if(now - TaskStartTime < task["ReleaseTime"]):                    
                    break
            if(len(putback) > 0):
                TaskQueue = putback + TaskQueue
            if(len(TaskQueue) == 0):
                # all tasks are distributed
                # check if all tasks are finished
                allTaskFinished = True
                for task in task_statistics.values():
                    if("res" not in task):
                        # logger.debug(f"[CTRL] Task[{task['taskid']}] not finished, deadline: {task['deadline']}")
                        allTaskFinished = False
                        break
                if(allTaskFinished):
                    logger.info(f"[CTRL] All tasks finished")
                    logger.info(f"{task_statistics.values()}")
                    missing_deadline_rate, missing_deadline_info, avg_finished_time, finished_info = statistics_compution(task_statistics)
                    logger.info(f"[CTRL] Missing deadline rate: {missing_deadline_rate}")
                    logger.info(f"[CTRL] Average finished time: {avg_finished_time}")
                    # use pickle to save the taks_statistics
                    # get now time format like 2021-04-01-12-00-00
                    now_time_string = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

                    with open(f"./taskdata/task_statistics_{now_time_string}.pkl", "wb") as f:
                        pickle.dump(task_statistics, f)
                    task_scatter(task_statistics, datafile=f"task_statistics_{now_time_string}.pkl")
                    # break the outer loop and exit
                    break
                        
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
            handler_id = int(args_dict["source"])
            # when received a ping signal from handler, which means handler changed their status
            if(SignalCommand[signal_command] == SignalCommand.PING):
                if(HandlerStatus[args_dict["status"]] == HandlerStatus.Load):
                    # send a signal to subprocess to ready(ready to run)
                    handler_status[handler_id] = HandlerStatus.Ready
                    signal_message = generate_signal(handler_id, SignalCommand.READY)
                    control_queue.put(signal_message)
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Ready):
                    # before all handlers are ready, we need to warmup the handlers
                    if(not all(allReady.values())):
                        if("warmup" in args_dict):
                            warmup[handler_id] += 1
                            if(warmup[handler_id] >= 5):
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
                handler_status[handler_id] = HandlerStatus.Ready
                taskid = args_dict["taskid"]
                if(args_dict["output"] == "success"):
                    # add output for dependency consuming
                    task_dependency[handler_id] += 1
                task_statistics[taskid]["res"] = args_dict["output"]
                task_statistics[taskid]["start_time"] = args_dict["start_time"]
                task_statistics[taskid]["end_time"] = args_dict["end_time"]
                logger.info(f"[CTRL] Task {args_dict['taskid']} finished, start time: {args_dict['start_time']}, end time: {args_dict['end_time']}")
            
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