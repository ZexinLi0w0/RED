import time, datetime
import pickle
import random
from collections import defaultdict
from AbstractHandler import HandlerStatus
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from visual_task import statistics_compution, task_scatter3
import logging

def liststr2list(s):
    return [i for i in s.strip('[').strip(']').split(',')]

def list2str(l):
    return ",".join([str(c) for c in l])
class TaskSchedule:
    def __init__(self, tasks, handler_status={}, control_queue = [], scheduler='priority', custom_scheduler=None, logger=logging, apporach_module='base_line'):
        self.tasks = tasks
        self.logger = logger
        # more approaches to adjust tasks, baseline(do nothing),
        # feedback(according to the feedback of task execution to adjust next release time),
        # fine-grained(reconstruct dag in task generation)  
        self.approach_module = apporach_module
        # control queue of signaling
        self.control_queue = control_queue
        # start time of generating tasks
        self.TaskStartTime = time.time()
        # Task Queue
        self.TaskQueue = []
        # statistics map of tasks Map<TaskId, TaskFinishedObject>
        self.task_statistics = defaultdict(dict)
        # dependency map of tasks Map<TaskId, Number of TaskOutput>
        self.task_dependency = defaultdict(int)
        # init dag_period of task_dependency
        for dag_period in range(10):
            self.task_dependency[dag_period] = defaultdict(int)

        # handler status to decide how to schedule
        self.handler_status = handler_status
        
        # scheduler
        self.default_scheduler = ['rr', 'priority', 'fcfs', 'fcls', 'edf']

        if(scheduler not in self.default_scheduler and scheduler != 'custom'):
            raise ValueError(f"Scheduler doesn't exist: {scheduler}")
        if(custom_scheduler is None and scheduler == 'custom'):
            raise ValueError("Custom scheduler is None")
        if(scheduler == 'custom'):
            self.scheduler_name = 'custom'
            self.scheduler = custom_scheduler
        else:
            self.scheduler_name = scheduler
            self.scheduler = self.__getattribute__(self.scheduler_name)
    
    def generate_task_list(self):
        TaskQueue = self.TaskQueue
        task_statistics = self.task_statistics
        TaskStartTime = time.time()
        self.TaskStartTime = TaskStartTime
        tasks_list = self.tasks
        logger = self.logger

        for task in tasks_list:
            handler_id = task["HandlerId"]
            taskid = f"--taskid {task['TaskId']}"
            release_time = f"--release_time {task['ReleaseTime']}"
            deadline = f"--deadline {task['Deadline']}"
            relative_time = f"--relative_time {TaskStartTime}" # relative start time of all tasks
            # only for simo
            simo_args = f"--simo_args {task['RunArgs']}"
            dag_period = f"--dag_period {task['DagPeriod']}"
            # create signal message and save it to task
            signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period)
            task['SignalMsg'] = signal_message
            TaskQueue.append(task)
            self.init_task_statistics(task)
            
        
        # offline Task schedule agorithm
        self.scheduler()
        logger.info(f"[CTRL] Tasks generated, start time: {TaskStartTime}, finished time: {time.time()}")

    def distribute_tasks(self):
        TaskQueue = self.TaskQueue
        TaskStartTime = self.TaskStartTime
        handler_status = self.handler_status        
        logger = self.logger

        putback = []
        while(len(TaskQueue) > 0):
            task = TaskQueue.pop(0)
            # distribute tasks
            signal_message = task['SignalMsg']
            now = time.time()
            
            # check if the task is ready to release, and the handler is ready to receive
            if(self.release_met(handler_status, task=task, now_time = now)):
                # send the signal to the handler
                self.send_signal(signal_message)
                logger.debug(f"[CTRL] Send task signal {signal_message} on {now-TaskStartTime} s")
            elif(self.missing_deadline_met(handler_status, task=task, now_time = now)):
                    # directly send this task
                    self.send_signal(signal_message)
                    continue
            else:
                # logger.debug(f"[CTRL] Put task back {signal_message} on {now-TaskStartTime} s")
                # put it back
                putback.append(task)
        if(len(putback) > 0):
            # put back the tasks with the same orders
            self.TaskQueue = putback + TaskQueue
            TaskQueue = self.TaskQueue
        if(len(TaskQueue) == 0):
            # all tasks are distributed
            if(self.all_task_finished()):
                self.after_finsihed_task_distribution()
                # declare the end of the task distribution
                return False
        return True
        
    def after_finsihed_task_distribution(self):
        """
        the method after all tasks are distributed and executed
        save the data for statistics and draw the scatter
        """
        logger = self.logger
        task_statistics = self.task_statistics
        logger.info(f"[CTRL] All tasks finished")
        # missing_deadline_rate, missing_deadline_info, avg_finished_time, finished_info = statistics_compution(task_statistics)
        # logger.info(f"[CTRL] Missing deadline rate: {missing_deadline_rate}")
        # logger.info(f"[CTRL] Average finished time: {avg_finished_time}")
        # use pickle to save the taks_statistics
        # get now time format like 2021-04-01-12-00-00
        now_time_string = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        relative_end2end_runtime = time.time() - self.TaskStartTime
        self.logger.info(f'[CTRL] Task End to End Finished time: {relative_end2end_runtime}')

        with open(f"./taskdata/task_statistics_{now_time_string}.pkl", "wb") as f:
            pickle.dump(task_statistics, f)
        task_scatter3(task_statistics, datafile=f"task_statistics_{now_time_string}.pkl")
        # break the outer loop and exit
        return

    def dependencies_met(self, task):
        task_dependency = self.task_dependency
        # only consume the dep within the same dag period
        dag_period = int(task["DagPeriod"]) or 1
        if(all(task_dependency[dag_period][i] >= 1 for i in task["Dependencies"])):
            for i in task["Dependencies"]:
                task_dependency[dag_period][i] -= 1            
            return True
        return False
    
    def release_met(self, handlers, task=None, now_time = time.time()):
        release_time = task["ReleaseTime"]
        handler_id = int(task["HandlerId"])
        TaskStartTime = self.TaskStartTime
        status = handlers[handler_id]

        return now_time - TaskStartTime >= release_time and status == HandlerStatus.Ready and self.dependencies_met(task)
    
    def all_task_finished(self):
        task_statistics = self.task_statistics
        for taskid in task_statistics:
            if("res" not in task_statistics[taskid]):
                return False
        return True
    
    def missing_deadline_met(self, handlers, task=None, now_time=time.time()):
        handler_id = int(task["HandlerId"])
        TaskStartTime = self.TaskStartTime
        status = handlers[handler_id]

        return (now_time - TaskStartTime) >= task["Deadline"] and status == HandlerStatus.Ready
    
    def send_signal(self, signal_message):
        # send the signal to the handler
        self.control_queue.put(signal_message)
    
    # dag adjustment approaches
    def feedback_adjust(self, end_time):
        # feedback(according to the feedback of task execution to adjust next release time)
        self.logger.debug(f'[CTRL] Feedback adjust endtime: {end_time} , {type(end_time)}')
        TaskQueue = self.TaskQueue
        if(len(TaskQueue)>0):
            task = TaskQueue.pop(0)
            task["ReleaseTime"] = end_time
            TaskQueue.append(task)
        self.TaskQueue = TaskQueue
    
    def fine_grained_adjust(self, merge_tick=0.02, merge_handler=[5]):
        """
        fine-grained(reconstruct dag in task generation), only works for SIMO/MIMO
        merge_tick: the time interval to merge two tasks
        merge_handler: the handler id can be considered merging
        """
        logger = self.logger
        TaskQueue = self.TaskQueue
        TaskStartTime = self.TaskStartTime
        putback = []
        prev = None
        # release time sorting to merge
        TaskQueue.sort(key=lambda x: x["ReleaseTime"])
        while(len(TaskQueue)):
            task = TaskQueue.pop(0)
            # try to merge if two tasks has close release time
            if(prev is not None):
                if(task["HandlerId"] in merge_handler and abs(prev["ReleaseTime"]-task["ReleaseTime"]) <= merge_tick and prev["DagPeriod"] == task["DagPeriod"]):
                    # merge the two tasks into one
                    """
                    TODO: merge rules
                    1. pick smaller release_time
                    2. pick larger deadline(lower missing deadlines)
                    3. fullfill the dependencies without repeated values
                    4. pick higher priority
                    5. fullfill the RunArgs without repeated values
                    6. merge the taskid as f'{taskid}_{prev_taskid}'
                    """
                    releaseTime = min(prev["ReleaseTime"], task["ReleaseTime"])
                    deadline = max(prev["Deadline"], task["Deadline"])
                    dependencies = list(set(prev["Dependencies"] + task["Dependencies"]))
                    priority = max(prev["Priority"], task["Priority"])
                    runArgs = list2str(list(set(liststr2list(prev["RunArgs"]) + liststr2list(task["RunArgs"]))))
                    taskId = f"{task['TaskId']}_{prev['TaskId']}"

                    # generate a new task and signal message as merging result
                    handler_id = task["HandlerId"]
                    taskid = f"--taskid {taskId}"
                    release_time = f"--release_time {releaseTime}"
                    deadline = f"--deadline {deadline}"
                    relative_time = f"--relative_time {TaskStartTime}" # relative start time of all tasks
                    simo_args = f"--simo_args {runArgs}"
                    dag_period = f"--dag_period {task['DagPeriod']}"
                    # create signal message and save it to task
                    signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period)
                    logger.debug(f'[CTRL] fine-grained merge two task: {signal_message}')
                    task['SignalMsg'] = signal_message
                    prev = task
                else:
                    putback.append(prev)
                    prev = task
            else:
                prev = task
        logger.debug(f'[CTRL] fine-grained merge result: {putback}')
        self.TaskQueue = putback





    def init_task_statistics(self, task):
        # record the task object for statistics
        self.task_statistics[task["TaskId"]] = {
            "handler_id":  task["HandlerId"],
            "taskid": task["TaskId"],
            "release_time": task["ReleaseTime"],
            "deadline": task["Deadline"],
            "priority": task["Priority"],
            "dependency": task["Dependencies"]
        }

    def add_task_statistics(self, taskid, result, start_time, end_time):
        self.task_statistics[taskid]["res"] = result
        self.task_statistics[taskid]["start_time"] = start_time
        self.task_statistics[taskid]["end_time"] = end_time
        self.logger.debug(f'[CTRL] [TASKSCHEDULER] Add Task Statistics data: {self.task_statistics[taskid]}')
    
    def add_task_output(self, dag_period, task_type):
        self.task_dependency[dag_period][task_type] += 1

    def rr(self):
        # round robin
        pass

    def fcfs(self):
        # first come first serve
        self.TaskQueue.sort(key=lambda x: (x["ReleaseTime"]))
    
    def fcls(self):
        # first come last serve
        self.TaskQueue.sort(key=lambda x: (x[1]["ReleaseTime"]), reverse=True)

    def priority(self):
        # priority
        self.TaskQueue.sort(key=lambda x: (x["Priority"]), reverse=True)

    def edf(self):
        
        # earliest deadline first
        self.TaskQueue.sort(key=lambda x: (x["Deadline"]))

if __name__ == "__main__":
    # test the task scheduler
    # create a task queue
    task_queue = []
    handler_status = defaultdict(int)
    for i in range(10):
        task_queue.append({
            "HandlerId": 1,
            "TaskId": i,
            "ReleaseTime": i,
            "Deadline": i+i,
            "Priority": random.randint(1, 10),
            "Dependencies": []
        })
    # create a task scheduler
    task_scheduler = TaskSchedule(task_queue, handler_status, [], scheduler='priority')
    task_scheduler.generate_task_list()
    prev = None
    for sign, task in task_scheduler.TaskQueue:
        if(prev is None):
            prev = task["Priority"]
            continue
        if(task["Priority"] > prev):
            print("Priority is not correct")
            raise Exception("Priority is not correct")
        prev = task["Priority"]
    print("Priority Test passed")

    task_scheduler = TaskSchedule(task_queue, handler_status, [], scheduler='edf')
    task_scheduler.generate_task_list()
    prev = None
    for sign, task in task_scheduler.TaskQueue:
        print(task)
        if(prev is None):
            prev = task["Deadline"]
            continue
        if(task["Deadline"] < prev):
            print("Deadline is not correct")
            raise Exception("Deadline is not correct")
        prev = task["Deadline"]
    print("Deadline Test passed")
    
