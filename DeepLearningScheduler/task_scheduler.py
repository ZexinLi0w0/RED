import time, datetime
import pickle
import random
from collections import defaultdict
from AbstractHandler import HandlerStatus
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from visual_task import statistics_compution, task_scatter3
import logging
from copy import deepcopy

def liststr2list(s):
    return [i for i in s.strip('[').strip(']').split(',')]

def list2str(l):
    return ",".join([str(c) for c in l])
class TaskSchedule:
    def __init__(self, tasks, handler_status={}, control_queue = [], scheduler='priority', custom_scheduler=None, logger=logging, approach_module='baseline'):
        self.tasks = tasks
        self.logger = logger
        # more approaches to adjust tasks, baseline(do nothing),
        # feedback(according to the feedback of task execution to adjust next release time),
        # fine-grained(reconstruct dag in task generation)  
        self.approach_module = approach_module
        # control queue of signaling
        self.control_queue = control_queue
        # start time of generating tasks
        self.TaskStartTime = time.time()
        # Task Queue
        self.TaskQueue = []
        # The number of tasks
        self.task_num = 0
        # The number of finished tasks
        self.finished_task_num = 0
        # statistics map of tasks Map<TaskId, TaskFinishedObject>
        self.task_statistics = defaultdict(dict)
        # dependency map of tasks Map<TaskId, Number of TaskOutput>
        self.task_dependency = defaultdict(int)

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
            # for feedback-fine-grained approach, add skipmode
            if(self.approach_module == 'feedback-fine-grained'):
                signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period, "--skipmode 1")
            else:    
                signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period)
            task['SignalMsg'] = signal_message
            TaskQueue.append(task)
            
        
        if(self.approach_module == 'fine-grained' or self.approach_module == 'feedback-fine-grained'):
            # reconstruct dag_period
            self.fine_grained_adjust()
        # offline Task schedule agorithm
        self.scheduler()
        self.task_num = len(self.TaskQueue)
        self.init_task_statistics()
        # logger.debug(f'[CTRL] Tasks: {TaskQueue}')
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
                
                # TODO: for now dag, it won't reduce the previous output when use it
                # consume dependencies
                # for dep in task["Dependencies"]:
                #     self.consume_task_output(task["DagPeriod"], dep)

                # send the signal to the handler
                self.send_signal(signal_message)
                # logger.debug(f"[CTRL] Send task signal {signal_message} on {now-TaskStartTime}")
            elif(self.missing_deadline_met(handler_status, task=task, now_time = now)):
                    # directly send this task
                    self.send_signal(signal_message)
                    continue
            else:
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
        # task_scatter3(task_statistics, datafile=f"task_statistics_{now_time_string}.pkl")
        # break the outer loop and exit
        return

    def dependencies_met(self, task):
        """
        check if the dependencies of the task are met
        """
        task_dependency = self.task_dependency
        # only consume the dep within the same dag period
        dag_period = int(task["DagPeriod"]) if task["DagPeriod"] is not None else 0
        # no dependency needs
        if(len(task["Dependencies"]) == 0):
            return True
        # no output provided
        if(dag_period not in task_dependency):
            return False
        # check if every dependency is met
        if(all(task_dependency[dag_period][i] >= 1 for i in task["Dependencies"])):
            return True
        return False
    
    def release_met(self, handlers, task=None, now_time = time.time()):
        """
        check if the release conditions are met
        """
        release_time = task["ReleaseTime"]
        handler_id = int(task["HandlerId"])
        TaskStartTime = self.TaskStartTime
        status = handlers[handler_id]

        return now_time - TaskStartTime >= release_time and status == HandlerStatus.Ready and self.dependencies_met(task)

    def consume_task_output(self, dag_period, task_type):
        dag_period = int(dag_period)
        task_type = int(task_type)
        if(dag_period not in self.task_dependency):
            self.task_dependency[dag_period] = defaultdict(int)
        self.task_dependency[dag_period][task_type] -= 1

    def add_task_output(self, dag_period, task_type):
        dag_period = int(dag_period)
        task_type = int(task_type)
        if(dag_period not in self.task_dependency):
            self.task_dependency[dag_period] = defaultdict(int)
        self.task_dependency[dag_period][task_type] += 1
    
    def all_task_finished(self):
        """
        check if all tasks are finished
        """
        return self.task_num == self.finished_task_num

    def finished_task(self, taskid, output, start_time, end_time):
        """
        finished one task and record the status
        """
        self.finished_task_num += 1
        self.add_task_statistics(taskid, output, start_time, end_time)

    def missing_deadline_met(self, handlers, task=None, now_time=time.time()):
        """
        check if the task is missing deadline
        """
        handler_id = int(task["HandlerId"])
        TaskStartTime = self.TaskStartTime
        status = handlers[handler_id]

        return (now_time - TaskStartTime) >= task["Deadline"] and status == HandlerStatus.Ready
    
    def send_signal(self, signal_message):
        """
        push signal to control queue
        """
        # send the signal to the handler
        self.control_queue.put(signal_message)
    
    # dag adjustment approaches
    def feedback_adjust(self, end_time):
        """
        adjust the release time of the next task according to the feedback of the previous task execution
        """
        TaskStartTime = self.TaskStartTime
        # feedback(according to the feedback of task execution to adjust next release time)
        TaskQueue = self.TaskQueue
        # self.logger.debug(f'[CTRL] adjust next task release time, tasknum: {len(TaskQueue)}')
        if(len(TaskQueue)>0):
            task = TaskQueue.pop(0)
            # self.logger.debug(f'[CTRL] Feedback adjust endtime, before {task["ReleaseTime"]}, after: {end_time}')
            if(end_time < task["ReleaseTime"]):
                task["ReleaseTime"] = end_time
                # adjust the data in task statistics
                self.task_statistics[task["TaskId"]]["release_time"] = end_time
                
                # generate new signal message
                handler_id = task["HandlerId"]
                taskid = f"--taskid {task['TaskId']}"
                release_time = f"--release_time {task['ReleaseTime']}"
                deadline = f"--deadline {task['Deadline']}"
                relative_time = f"--relative_time {TaskStartTime}" # relative start time of all tasks
                # only for simo
                simo_args = f"--simo_args {task['RunArgs']}"
                dag_period = f"--dag_period {task['DagPeriod']}"
                # create signal message and save it to task
                # for feedback-fine-grained approach, add skipmode
                if(self.approach_module == 'feedback-fine-grained'):
                    signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period, "--skipmode 1")
                else:    
                    signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period)
                task['SignalMsg'] = signal_message
            TaskQueue.insert(0, task)
        self.TaskQueue = TaskQueue
    
    def fine_grained_adjust(self, merge_tick=0.02, merge_handler=[5]):
        """
        fine-grained(reconstruct dag in task generation), only works for SIMO/MIMO
        merge_tick: the time interval to merge two tasks
        merge_handler: the handler id can be considered merging
        """
        logger = self.logger
        TaskQueue = self.TaskQueue
        logger.debug(f'[CTRL] fine-grained adjust, tasknum: {len(TaskQueue)}')
        TaskStartTime = self.TaskStartTime
        putback = []
        merged_task = []
        # release time sorting to merge
        TaskQueue.sort(key=lambda x: x["ReleaseTime"])
        while(len(TaskQueue)):
            task = TaskQueue.pop(0)
            if(task["HandlerId"] not in merge_handler):
                putback.append(task)
                continue
            # compare to all remained tasks to merge
            putback = []
            while(len(TaskQueue)):
                other_task = TaskQueue.pop(0)
                if(abs(other_task["ReleaseTime"]-task["ReleaseTime"]) <= merge_tick and other_task["DagPeriod"] == task["DagPeriod"]):
                    # merge the two tasks
                    """
                    TODO: merge rules
                    1. pick smaller release_time
                    2. pick larger deadline(lower missing deadlines)
                    3. fullfill the dependencies without repeated values
                    4. pick higher priority
                    5. fullfill the RunArgs without repeated values
                    6. merge the taskid as f'{taskid}_{other_taskid}'
                    """
                    # merge the two tasks
                    new_task = {
                        "TaskId": f"{task['TaskId']}_{other_task['TaskId']}",
                        "DagPeriod": task["DagPeriod"],
                        "HandlerId": task["HandlerId"], # always 5
                        "ReleaseTime": min(other_task["ReleaseTime"], task["ReleaseTime"]),
                        "Deadline": max(other_task["Deadline"], task["Deadline"]), # deadline won't extend for ReleaseTimeDelay
                        "Priority": max(other_task["Priority"], task["Priority"]),
                        "Dependencies": list(set(other_task["Dependencies"] + task["Dependencies"])),
                        "RunArgs": list2str(list(set(liststr2list(other_task["RunArgs"]) + liststr2list(task["RunArgs"])))),
                    }
                    handler_id = new_task["HandlerId"]
                    taskid = f"--taskid {new_task['TaskId']}"
                    release_time = f"--release_time {new_task['ReleaseTime']}"
                    deadline = f"--deadline {new_task['Deadline']}"
                    relative_time = f"--relative_time {TaskStartTime}" # relative start time of all tasks
                    # only for simo
                    simo_args = f"--simo_args {new_task['RunArgs']}"
                    dag_period = f"--dag_period {new_task['DagPeriod']}"
                    # create signal message and save it to task
                    # for feedback-fine-grained approach, add skipmode
                    if(self.approach_module == 'feedback-fine-grained'):
                        signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period, "--skipmode 1")
                    else:    
                        signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period)
                    logger.debug(f'[CTRL] fine-grained merge two task: {signal_message}')
                    
                    task = new_task
                    task['SignalMsg'] = signal_message
                else:
                    putback.append(other_task)
            TaskQueue = putback
            merged_task.append(task)
        
        logger.debug(f'[CTRL] fine-grained merge result: {len(merged_task)}')
        self.TaskQueue = merged_task

    def init_task_statistics(self):
        """
        generate a task statistics dict for drawing and analysis
        """
        # record the task object for statistics
        task_statistics = defaultdict(dict)
        for task in self.TaskQueue:
            task_statistics[task["TaskId"]] = {
                "handler_id":  task["HandlerId"],
                "taskid": task["TaskId"],
                "release_time": task["ReleaseTime"],
                "deadline": task["Deadline"],
                "priority": task["Priority"],
                "dependency": task["Dependencies"],
                "dag_period": task["DagPeriod"],
                "simo_args": task["RunArgs"],
            }
        self.task_statistics = task_statistics

    def add_task_statistics(self, taskid, result, start_time, end_time):
        self.task_statistics[taskid]["res"] = result
        self.task_statistics[taskid]["start_time"] = start_time
        self.task_statistics[taskid]["end_time"] = end_time        


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
    
