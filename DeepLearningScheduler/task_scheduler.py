import time, datetime
import pickle
import random
from collections import defaultdict
from AbstractHandler import HandlerStatus
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from visual_scripts.visual_task import statistics_compution, task_scatter3
import logging
from copy import deepcopy
from burst_task_manager import BurstTaskManager, BurstAwareTaskScheduler

def liststr2list(s):
    return [i for i in s.strip('[').strip(']').split(',')]

def list2str(l):
    return ",".join([str(c) for c in l])
class TaskSchedule:
    def __init__(self, tasks, handler_status={}, control_queue = [], scheduler='priority', custom_scheduler=None, logger=logging, approach_module='baseline', task_filename='task_config', burst_enabled=False, burst_config=None):
        self.tasks = tasks
        self.logger = logger
        # more approaches to adjust tasks, baseline(do nothing),
        # feedback(according to the feedback of task execution to adjust next release time),
        # fine-grained(reconstruct dag in task generation)  
        self.approach_module = approach_module
        # record the task config name for generate the naem of data file to save
        self.task_filename = task_filename
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
        
        # Burst task management
        self.burst_enabled = burst_enabled
        if burst_enabled:
            burst_config = burst_config or {}
            gpu_threshold = burst_config.get('gpu_threshold', 80.0)
            queue_threshold = burst_config.get('queue_threshold', 10)
            default_drop_threshold = burst_config.get('drop_threshold', 0.5)
            monitoring_interval = burst_config.get('monitoring_interval', 0.05)
            self.burst_manager = BurstTaskManager(
                gpu_threshold=gpu_threshold,
                queue_threshold=queue_threshold,
                default_drop_threshold=default_drop_threshold,
                monitoring_interval=monitoring_interval,
                logger=logger
            )
            self.burst_scheduler = BurstAwareTaskScheduler(
                burst_manager=self.burst_manager,
                base_scheduler=self.scheduler_name,
                logger=logger
            )
            # Start burst monitoring
            self.burst_manager.start_monitoring()
            self.logger.info(f"[BURST] Burst task management enabled with GPU threshold: {gpu_threshold}%, Queue threshold: {queue_threshold}")
        else:
            self.burst_manager = None
            self.burst_scheduler = None
    
    def generate_task_list(self):
        TaskQueue = self.TaskQueue
        TaskStartTime = time.time()
        tasks_list = self.tasks
        logger = self.logger

        for task in tasks_list:
            handler_id = task["HandlerId"]
            taskid = f"--taskid {task['TaskId']}"
            release_time = f"--release_time {task['ReleaseTime']}"
            deadline = f"--deadline {task['Deadline']}"
            relative_time = f"--relative_time {TaskStartTime}" # relative start time of all tasks
            # only for simo
            simo_args = f"--simo_args {task['RunArgs']}" if 'RunArgs' in task else ""
            dag_period = f"--dag_period {task['DagPeriod']}" if 'DagPeriod' in task else ""
            non_partitionable_flag = "--non_partitionable true" if task.get("IsNonPartitionable", False) else ""
            # create signal message and save it to task
            # for feedback-fine-grained approach, add skipmode
            if(self.approach_module == 'feedback-fine-grained'):
                signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period, non_partitionable_flag, "--skipmode 1")
            else:    
                signal_message = generate_signal(handler_id, SignalCommand.RUN, release_time, deadline, relative_time, taskid, simo_args, dag_period, non_partitionable_flag)
            task['SignalMsg'] = signal_message
            TaskQueue.append(task)
            
        
        if(self.approach_module == 'fine-grained' or self.approach_module == 'feedback-fine-grained'):
            # reconstruct dag_period
            self.fine_grained_adjust()
        # offline Task schedule algorithm
        if self.burst_enabled and self.burst_scheduler:
            # Use burst-aware scheduling
            # Use time relative to TaskStartTime so it aligns with task ReleaseTime/Deadline units
            current_time = time.time() - TaskStartTime
            scheduled_tasks, dropped_tasks = self.burst_scheduler.schedule_tasks(self.TaskQueue, current_time)
            # Handle dropped tasks (record as dropped before scheduling proceeds)
            for dropped_task in dropped_tasks:
                self.handle_dropped_task(dropped_task.get('TaskId', 'Unknown'))
            self.TaskQueue = scheduled_tasks
        else:
            # Use original scheduling
            if hasattr(self, 'scheduler_name') and self.scheduler_name in ['edf', 'priority', 'fcfs', 'fcls']:
                # Call the scheduler method directly
                scheduler_method = getattr(self, self.scheduler_name)
                scheduler_method()
            else:
                self.scheduler()
        
        self.task_num = len(self.TaskQueue)
        self.init_task_statistics()
        self.TaskStartTime = TaskStartTime
        # logger.debug(f'[CTRL] Tasks: {TaskQueue}')
        logger.info(f"[CTRL] Tasks generated, start time: {TaskStartTime}, finished time: {time.time()}")
        # logger.debug(f"[DEBUG] edf scheduler, TaskQueue: {self.TaskQueue}")
        # check if task queue satisfy the earlier deadline first
        # prev = None
        # for task in self.TaskQueue:
        #     if(prev is None):
        #         prev = task["Deadline"]
        #         continue
        #     if(task["Deadline"] < prev):
        #         print("Deadline is not correct")
        #         raise Exception("Deadline is not correct")
        #     prev = task["Deadline"]
        # print("Deadline Test passed")

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
        
        # Apply burst-aware scheduling to putback tasks if enabled
        if self.burst_enabled and self.burst_scheduler and len(putback) > 0:
            # Use time relative to TaskStartTime for consistent criticality calculation
            current_time = time.time() - TaskStartTime
            remaining_tasks, dropped_tasks = self.burst_scheduler.burst_manager.proactive_drop(putback, current_time)
            
            # Handle dropped tasks
            for dropped_task in dropped_tasks:
                self.handle_dropped_task(dropped_task.get('TaskId', 'Unknown'))
            
            putback = remaining_tasks
        
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
        now = time.time()
        relative_end2end_runtime = now - self.TaskStartTime
        
        # Log burst statistics if enabled
        if self.burst_enabled and self.burst_manager:
            burst_stats = self.burst_manager.get_burst_statistics()
            logger.info(f"[BURST] burst statistics: {burst_stats}")
            # Stop burst monitoring
            self.burst_manager.stop_monitoring()
        
        # use pickle to save the taks_statistics
        # get now time format like 2021-04-01-12-00-00
        import os
        now_time_string = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        # Always use relative ./taskdata under the runtime root
        raw_data_save_path = os.path.join(os.getcwd(), 'taskdata')
        os.makedirs(raw_data_save_path, exist_ok=True)
        end2end_path = os.path.join(raw_data_save_path, f"end2endtime_{self.task_filename}_{self.approach_module}_{now_time_string}.txt")
        stats_path = os.path.join(raw_data_save_path, f"statistics_{self.task_filename}_{self.approach_module}_{now_time_string}.pkl")
        with open(end2end_path, "w") as f:
            f.write(str(relative_end2end_runtime))
        with open(stats_path, "wb") as f:
            pickle.dump(task_statistics, f)
        logger.info(f"[CTRL] Saved end2end time to: {end2end_path}")
        logger.info(f"[CTRL] Saved statistics to: {stats_path}")
        self.logger.info(f'[CTRL] Task End to End Finished time: {relative_end2end_runtime}')
        missing_deadline_rate, missing_deadline_info, avg_finished_time, finished_info, metrics = statistics_compution(task_statistics, task_config_path = f"{self.task_filename}.json", now_time = now, task_start_time = self.TaskStartTime)
        logger.info(f"[CTRL] SubTask Missing deadline rate: {missing_deadline_rate}")
        logger.info(f"[CTRL] SubTask Average finished time: {avg_finished_time}")
        logger.info(f"[CTRL] Task Metrics: {metrics}")

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

    def skipped_dependent_tasks(self, taskid, dag_period, dep, now_time=time.time()):
        self.logger.debug(f'[DEBUG]drop following tasks with {dag_period}, dep: {dep}')
        dropped = []
        for task in self.TaskQueue:
            if(int(task['DagPeriod']) == int(dag_period) and dep in task['Dependencies']):
                dropped.append(task)
                continue
        self.logger.debug(f'[DEBUG]drop following tasks: {[task["TaskId"] for task in dropped]}')
        for task in dropped:
            taskid = task["TaskId"]
            self.finished_task(taskid, 'skip', now_time, now_time)
            # remove task from self.TaskQueue
            self.TaskQueue.remove(task)
                    
    
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
    
    def handle_dropped_task(self, taskid, reason="burst_drop"):
        """
        Handle a task that was dropped due to burst management
        """
        self.finished_task_num += 1
        now = time.time()
        self.add_task_statistics(taskid, reason, now, now)
        self.logger.info(f"[BURST] Task {taskid} dropped due to {reason}")

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
            # Skip merging for non-partitionable tasks
            if task.get("IsNonPartitionable", False):
                merged_task.append(task)
                continue
            if(task["HandlerId"] not in merge_handler):
                putback.append(task)
                continue
            # compare to all remained tasks to merge
            putback = []
            while(len(TaskQueue)):
                other_task = TaskQueue.pop(0)
                # Also skip merging for non-partitionable tasks
                if other_task.get("IsNonPartitionable", False):
                    putback.append(other_task)
                    continue
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
                        "IsNonPartitionable": False,
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
                "dag_period": task.get("DagPeriod", None),
                "simo_args": task.get("RunArgs", ""),
                "is_non_partitionable": task.get("IsNonPartitionable", False),
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
    from task_generator import load_dag_config, generate_tasks_from_dag
    result = load_dag_config("TaskConfigs/simo-baseline-nano.json")
    if result is None:
        print("Error: Failed to load DAG config")
        exit(1)
    dag_config, factor, non_partitionable_percentage, non_partitionable_config = result
    tasks = generate_tasks_from_dag(dag_config, time_factor=factor, non_partitionable_percentage=non_partitionable_percentage, non_partitionable_config=non_partitionable_config)
    handler_status = defaultdict(int)
    # create a task scheduler
    # task_scheduler = TaskSchedule(tasks, handler_status, [], scheduler='priority')
    # task_scheduler.generate_task_list()
    # prev = None
    # for task in task_scheduler.TaskQueue:
    #     if(prev is None):
    #         prev = task["Priority"]
    #         continue
    #     if(task["Priority"] > prev):
    #         print("Priority is not correct")
    #         raise Exception("Priority is not correct")
    #     prev = task["Priority"]
    # print("Priority Test passed")

    task_scheduler = TaskSchedule(tasks, handler_status, [], scheduler='edf')
    task_scheduler.generate_task_list()
    prev = None
    
    for task in task_scheduler.TaskQueue:
        print(task)
        if(prev is None):
            prev = task["Deadline"]
            continue
        if(task["Deadline"] < prev):
            print("Deadline is not correct")
            raise Exception("Deadline is not correct")
        prev = task["Deadline"]
    print("Deadline Test passed")
    
