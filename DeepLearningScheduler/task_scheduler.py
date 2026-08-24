import time, datetime
import hashlib
import json
import os
import pickle
from collections import Counter, defaultdict
from AbstractHandler import HandlerStatus
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from visual_scripts.visual_task import statistics_compution, task_scatter3
import logging
from copy import deepcopy
from burst_task_manager import BurstTaskManager
from task_generator import task_stream_sha256
from matrics import DEFAULT_XRBENCH_RT_K, VALID_OUTPUT_OUTCOMES

def liststr2list(s):
    return [i for i in s.strip('[').strip(']').split(',')]

def list2str(l):
    return ",".join([str(c) for c in l])


def _constituent_task_ids(task):
    return list(task.get("ConstituentTaskIds", [task["TaskId"]]))


def tasks_merge_eligible(first, second, merge_tick):
    """Return whether two execution nodes represent the same mergeable stage."""
    if first.get("IsNonPartitionable", False) or second.get(
        "IsNonPartitionable", False
    ):
        return False
    if first.get("HandlerId") != second.get("HandlerId"):
        return False
    if first.get("DagPeriod") != second.get("DagPeriod"):
        return False
    if not first.get("MergeKey") or first.get("MergeKey") != second.get(
        "MergeKey"
    ):
        return False
    return abs(first["ReleaseTime"] - second["ReleaseTime"]) <= merge_tick


def merge_tasks(first, second):
    """Create one execution node while preserving both reporting populations."""
    if first.get("MergeKey") != second.get("MergeKey"):
        raise ValueError("cannot merge tasks from different structural stages")

    constituent_ids = sorted(
        set(_constituent_task_ids(first) + _constituent_task_ids(second))
    )
    merged_identity = hashlib.sha256(
        "\n".join(constituent_ids).encode("utf-8")
    ).hexdigest()[:16]
    run_args = sorted(
        set(liststr2list(first["RunArgs"]) + liststr2list(second["RunArgs"])),
        key=lambda value: int(value),
    )

    return {
        "TaskId": f"merged_{merged_identity}",
        "TaskPosition": f"merged:{first['MergeKey']}",
        "MergeKey": first["MergeKey"],
        "ConstituentTaskIds": constituent_ids,
        "DagPeriod": first["DagPeriod"],
        "HandlerId": first["HandlerId"],
        "ReleaseTime": min(first["ReleaseTime"], second["ReleaseTime"]),
        # A merged execution must satisfy the earliest constituent deadline.
        "Deadline": min(first["Deadline"], second["Deadline"]),
        "Priority": max(first["Priority"], second["Priority"]),
        "Dependencies": sorted(
            set(first["Dependencies"] + second["Dependencies"])
        ),
        "RunArgs": list2str(run_args),
        "IsNonPartitionable": False,
    }


def _task_output_types(task):
    run_args = task.get("RunArgs", [])
    if isinstance(run_args, str):
        values = liststr2list(run_args)
    else:
        values = list(run_args)
    return {int(value) for value in values if str(value).strip()}


def remaining_critical_path_costs(tasks):
    """Compute profiled remaining critical-path cost for each offered DAG node."""
    task_by_id = {task["TaskId"]: task for task in tasks}
    if len(task_by_id) != len(tasks):
        raise ValueError("TaskId values must be unique")

    grouped_tasks = defaultdict(list)
    for task in tasks:
        required_fields = {
            "DagIndex",
            "DagPeriod",
            "StageIndex",
            "EstimatedExecutionTime",
        }
        missing = sorted(required_fields - set(task))
        if missing:
            raise ValueError(
                f"task {task['TaskId']} lacks LLF-DAG fields: {missing}"
            )
        grouped_tasks[(task["DagIndex"], task["DagPeriod"])].append(task)

    successors = {task_id: set() for task_id in task_by_id}
    for group in grouped_tasks.values():
        for task in group:
            task_stage = task["StageIndex"]
            for dependency in task.get("Dependencies", []):
                candidates = [
                    predecessor
                    for predecessor in group
                    if predecessor["StageIndex"] < task_stage
                    and int(dependency) in _task_output_types(predecessor)
                ]
                if not candidates:
                    continue
                latest_stage = max(
                    predecessor["StageIndex"] for predecessor in candidates
                )
                for predecessor in candidates:
                    if predecessor["StageIndex"] == latest_stage:
                        successors[predecessor["TaskId"]].add(task["TaskId"])

    remaining_costs = {}
    tasks_by_reverse_stage = sorted(
        tasks,
        key=lambda task: (
            task["DagIndex"],
            task["DagPeriod"],
            task["StageIndex"],
            task["TaskId"],
        ),
        reverse=True,
    )
    for task in tasks_by_reverse_stage:
        successor_cost = max(
            (
                remaining_costs[successor_id]
                for successor_id in successors[task["TaskId"]]
            ),
            default=0.0,
        )
        remaining_costs[task["TaskId"]] = (
            float(task["EstimatedExecutionTime"]) + successor_cost
        )

    return remaining_costs


def annotate_remaining_critical_path_costs(tasks):
    costs = remaining_critical_path_costs(tasks)
    for task in tasks:
        task["RemainingCriticalPathCost"] = costs[task["TaskId"]]
    return tasks


class TaskSchedule:
    def __init__(self, tasks, handler_status=None, control_queue=None, scheduler='priority', custom_scheduler=None, logger=logging, approach_module='baseline', task_filename='task_config', burst_enabled=False, burst_config=None, burst_task_ratio=0, task_config_path=None, output_dir=None, run_id=None, merge_tick_seconds=0.02):
        self.tasks = tasks
        self.logger = logger
        # more approaches to adjust tasks, baseline(do nothing),
        # feedback(according to the feedback of task execution to adjust next release time),
        # fine-grained(reconstruct dag in task generation)  
        self.approach_module = approach_module
        # record the task config name for generate the naem of data file to save
        self.task_filename = task_filename
        self.task_config_path = task_config_path or f"{task_filename}.json"
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'taskdata')
        self.run_id = run_id
        if merge_tick_seconds < 0:
            raise ValueError("merge_tick_seconds cannot be negative")
        self.merge_tick_seconds = float(merge_tick_seconds)
        # control queue of signaling
        self.control_queue = [] if control_queue is None else control_queue
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
        self.handler_status = {} if handler_status is None else handler_status
        
        # scheduler
        self.default_scheduler = ['rr', 'priority', 'fcfs', 'fcls', 'edf', 'llf_dag']

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
            # Start burst monitoring
            self.burst_manager.start_monitoring()
            self.logger.info(f"[BURST] Burst task management enabled with GPU threshold: {gpu_threshold}%, Queue threshold: {queue_threshold}")
        else:
            self.burst_manager = None
        self.burst_task_ratio = burst_task_ratio or 0
        self._burst_tasks_augmented = False
        self.offered_task_stream_hash = task_stream_sha256(tasks)
    
    def generate_task_list(self):
        TaskQueue = self.TaskQueue
        TaskStartTime = time.time()
        # Set self.TaskStartTime early so it's available for fine_grained_adjust()
        self.TaskStartTime = TaskStartTime
        if self.burst_enabled and self.burst_manager and self.burst_task_ratio > 0 and not self._burst_tasks_augmented:
            extra_tasks = self.burst_manager.generate_burst_tasks(self.tasks, self.burst_task_ratio)
            if extra_tasks:
                self.logger.info(f"[BURST] Augmenting task list with {len(extra_tasks)} burst tasks (ratio={self.burst_task_ratio}%).")
                self.tasks = self.tasks + extra_tasks
            self._burst_tasks_augmented = True
        tasks_list = self.tasks
        for task in tasks_list:
            task.setdefault("ConstituentTaskIds", [task["TaskId"]])
        self.offered_tasks_by_id = {
            task["TaskId"]: deepcopy(task) for task in tasks_list
        }
        self.offered_task_stream_hash = task_stream_sha256(tasks_list)
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
            self.fine_grained_adjust(merge_tick=self.merge_tick_seconds)
        if self.scheduler_name == 'llf_dag':
            annotate_remaining_critical_path_costs(self.TaskQueue)
        # offline Task schedule algorithm (baseline only)
        if hasattr(self, 'scheduler_name') and self.scheduler_name in ['edf', 'priority', 'fcfs', 'fcls']:
            # Call the scheduler method directly
            scheduler_method = getattr(self, self.scheduler_name)
            scheduler_method()
        else:
            self.scheduler()
        
        self.task_num = len(self.TaskQueue)
        self.init_task_statistics()
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

        if self.scheduler_name == 'llf_dag':
            self.llf_dag(now_relative=time.time() - TaskStartTime)
            TaskQueue = self.TaskQueue

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
        if self.burst_enabled and self.burst_manager and len(putback) > 0:
            # Use time relative to TaskStartTime for consistent criticality calculation
            current_time = time.time() - TaskStartTime
            remaining_tasks, dropped_tasks = self.burst_manager.proactive_drop(putback, current_time)
            
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

        burst_stats = None
        # Log burst statistics if enabled
        if self.burst_enabled and self.burst_manager:
            burst_stats = self.burst_manager.get_burst_statistics()
            # Stop burst monitoring
            self.burst_manager.stop_monitoring()

        now_time_string = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        raw_data_save_path = self.output_dir
        os.makedirs(raw_data_save_path, exist_ok=True)
        if self.run_id:
            end2end_path = os.path.join(raw_data_save_path, "end2end_time.txt")
            stats_path = os.path.join(raw_data_save_path, "task_statistics.pkl")
            summary_path = os.path.join(raw_data_save_path, "summary.json")
        else:
            artifact_stem = (
                f"{self.task_filename}_{self.approach_module}_{now_time_string}"
            )
            end2end_path = os.path.join(
                raw_data_save_path, f"end2endtime_{artifact_stem}.txt"
            )
            stats_path = os.path.join(
                raw_data_save_path, f"statistics_{artifact_stem}.pkl"
            )
            summary_path = os.path.join(
                raw_data_save_path, f"summary_{artifact_stem}.json"
            )
        with open(end2end_path, "w") as f:
            f.write(str(relative_end2end_runtime))
        with open(stats_path, "wb") as f:
            pickle.dump(task_statistics, f)
        logger.info(f"[CTRL] Saved end2end time to: {end2end_path}")
        logger.info(f"[CTRL] Saved statistics to: {stats_path}")
        self.logger.info(f'[CTRL] Task End to End Finished time: {relative_end2end_runtime}')
        missing_deadline_rate, missing_deadline_info, avg_finished_time, finished_info, metrics = statistics_compution(
            task_statistics,
            task_config_path=self.task_config_path,
            now_time=now,
            task_start_time=self.TaskStartTime,
        )
        logger.info(f"[CTRL] SubTask Missing deadline rate: {missing_deadline_rate}")
        logger.info(f"[CTRL] SubTask Average finished time: {avg_finished_time}")
        logger.info(f"[CTRL] Task Metrics: {metrics}")

        outcome_counts = Counter(
            task["res"] for task in task_statistics.values()
        )
        valid_output_count = sum(
            outcome_counts[outcome] for outcome in VALID_OUTPUT_OUTCOMES
        )
        summary = {
            "schema_version": 1,
            "run_id": self.run_id,
            "method": self.approach_module,
            "torch_device": os.environ.get(
                "RED_TORCH_DEVICE_RESOLVED", "unrecorded"
            ),
            "merge_threshold_ms": self.merge_tick_seconds * 1000.0,
            "task_config_path": self.task_config_path,
            "offered_task_stream_sha256": self.offered_task_stream_hash,
            "offered_task_count": len(task_statistics),
            "execution_task_count": self.task_num,
            "finished_execution_task_count": self.finished_task_num,
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "end_to_end_latency_seconds": relative_end2end_runtime,
            "deadline_missing_rate": missing_deadline_rate,
            "average_executed_node_latency_seconds": avg_finished_time,
            "overall_deadline_hit": metrics[1],
            "qoe_score": metrics[2],
            "qoe_score_definition": (
                "mean XRBench real-time sigmoid utility over offered nodes; "
                "non-valid outputs score zero"
            ),
            "xrbench_rt_k_per_second": DEFAULT_XRBENCH_RT_K,
            "valid_output_rate": valid_output_count / len(task_statistics),
            "burst_statistics": burst_stats,
        }
        temporary_summary_path = f"{summary_path}.tmp"
        with open(temporary_summary_path, "w", encoding="utf-8") as summary_file:
            json.dump(summary, summary_file, indent=2, sort_keys=True)
            summary_file.write("\n")
        os.replace(temporary_summary_path, summary_path)
        logger.info(f"[CTRL] Saved run summary to: {summary_path}")
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
    
    def fine_grained_adjust(self, merge_tick=0.02, merge_handler=None):
        """
        fine-grained(reconstruct dag in task generation), only works for SIMO/MIMO
        merge_tick: the time interval to merge two tasks
        merge_handler: the handler id can be considered merging
        """
        logger = self.logger
        merge_handlers = set([5] if merge_handler is None else merge_handler)
        pending = sorted(self.TaskQueue, key=lambda task: task["ReleaseTime"])
        merged_queue = []
        logger.debug(f'[CTRL] fine-grained adjust, tasknum: {len(pending)}')

        while pending:
            task = pending.pop(0)
            remaining = []
            for other_task in pending:
                if (
                    task["HandlerId"] in merge_handlers
                    and tasks_merge_eligible(task, other_task, merge_tick)
                ):
                    task = merge_tasks(task, other_task)
                else:
                    remaining.append(other_task)
            pending = remaining

            if len(_constituent_task_ids(task)) > 1:
                handler_id = task["HandlerId"]
                signal_parts = [
                    f"--release_time {task['ReleaseTime']}",
                    f"--deadline {task['Deadline']}",
                    f"--relative_time {self.TaskStartTime}",
                    f"--taskid {task['TaskId']}",
                    f"--simo_args {task['RunArgs']}",
                    f"--dag_period {task['DagPeriod']}",
                ]
                if self.approach_module == 'feedback-fine-grained':
                    signal_parts.append("--skipmode 1")
                task['SignalMsg'] = generate_signal(
                    handler_id, SignalCommand.RUN, *signal_parts
                )
                logger.debug(
                    f"[CTRL] fine-grained merged execution: {task['TaskId']}"
                )
            merged_queue.append(task)

        logger.debug(f'[CTRL] fine-grained merge result: {len(merged_queue)}')
        self.TaskQueue = merged_queue

    def init_task_statistics(self):
        """
        generate a task statistics dict for drawing and analysis
        """
        # Record outcomes against the original offered-node population. Merged
        # execution nodes therefore do not change the metric denominator.
        task_statistics = defaultdict(dict)
        execution_to_constituents = {}
        for execution_task in self.TaskQueue:
            constituent_ids = _constituent_task_ids(execution_task)
            execution_to_constituents[execution_task["TaskId"]] = constituent_ids
            for task_id in constituent_ids:
                task = self.offered_tasks_by_id[task_id]
                task_statistics[task_id] = {
                    "handler_id": task["HandlerId"],
                    "taskid": task_id,
                    "release_time": task["ReleaseTime"],
                    "deadline": task["Deadline"],
                    "priority": task["Priority"],
                    "dependency": task["Dependencies"],
                    "dag_period": task.get("DagPeriod", None),
                    "simo_args": task.get("RunArgs", ""),
                    "is_non_partitionable": task.get(
                        "IsNonPartitionable", False
                    ),
                    "execution_task_id": execution_task["TaskId"],
                }
        self.execution_to_constituents = execution_to_constituents
        self.task_statistics = task_statistics

    def add_task_statistics(self, taskid, result, start_time, end_time):
        constituent_ids = self.execution_to_constituents.get(taskid, [taskid])
        for constituent_id in constituent_ids:
            task_statistics = self.task_statistics[constituent_id]
            constituent_result = result
            if result in {"success", "failure"}:
                constituent_result = (
                    "success"
                    if float(end_time) <= float(task_statistics["deadline"])
                    else "failure"
                )
            task_statistics["res"] = constituent_result
            task_statistics["start_time"] = start_time
            task_statistics["end_time"] = end_time


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

    def llf_dag(self, now_relative=None):
        """Least-laxity-first using the profiled remaining DAG critical path."""
        if now_relative is None:
            now_relative = max(0.0, time.time() - self.TaskStartTime)

        def llf_key(task):
            remaining_cost = float(task["RemainingCriticalPathCost"])
            laxity = float(task["Deadline"]) - now_relative - remaining_cost
            task["CurrentLaxity"] = laxity
            return (
                laxity,
                float(task["Deadline"]),
                float(task["ReleaseTime"]),
                task["TaskId"],
            )

        self.TaskQueue.sort(key=llf_key)

if __name__ == "__main__":
    # test the task scheduler
    from task_generator import load_dag_config, generate_tasks_from_dag
    result = load_dag_config("TaskConfigs/simo-baseline-nano.json")
    if result is None:
        print("Error: Failed to load DAG config")
        exit(1)
    dag_config, factor, non_partitionable_percentage, non_partitionable_config, burst_task_ratio = result
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

    task_scheduler = TaskSchedule(tasks, handler_status, [], scheduler='edf', burst_task_ratio=burst_task_ratio)
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
    
