import json
from nanoid import generate

# Required Attributes for TaskConfigObject
TaskConfigAttributes = ["HandlerId", "Period", "Deadline", "RunningTime", "Priority", "Dependencies"]

def validate_task_config(task_config):
    """
    Function to validate the task configs.
    """
    # Validate the task attributes
    for i, task in enumerate(task_config):
        # Check if the task has all required attributes
        missing_attrs = []
        for attr in TaskConfigAttributes:
            if attr not in task:
                missing_attrs.append(attr)
        if missing_attrs:
            raise ValueError(f"Invalid task #{i+1}: missing required attribute(s): {', '.join(missing_attrs)}")
        
        # Check if the dependencies attribute is a list
        if not isinstance(task["Dependencies"], list):
            raise ValueError(f"Invalid task #{i+1}: Dependencies must be a list in task id[{task['HandlerId']}]")
        if not isinstance(task["Priority"], int):
            raise ValueError(f"Invalid task #{i+1}: Priority must be an int in task id[{task['HandlerId']}]")
        if not isinstance(task["Deadline"], float):
            raise ValueError(f"Invalid task #{i+1}: Deadline must be a float in task id[{task['HandlerId']}]")
        if not isinstance(task["Period"], int):
            raise ValueError(f"Invalid task #{i+1}: Period must be an int in task id[{task['HandlerId']}]")
        if not isinstance(task["RunningTime"], int):
            raise ValueError(f"Invalid task #{i+1}: RunningTime must be an int in task id[{task['HandlerId']}]")
        if "ReleaseTimeDelay" in task:
            if not isinstance(task["ReleaseTimeDelay"], float) and not isinstance(task["ReleaseTimeDelay"], int):
                raise ValueError(f"Invalid task #{i+1}: ReleaseTimeDelay must be a float in task id[{task['HandlerId']}]")
        else:
            task["ReleaseTimeDelay"] = 0.0

def load_task_config(task_config_path):
    """
    Load a task config from a JSON file.
    Task Configuration:
    {
        "task_list": List<TaskConfigObject>
    }

    TaskConfigObject Attributes:

    HandlerId: the handler id of tasks
    Period: the amount of each task per 1 second, e.g. 30(fps) mean 30 tasks per 1 seconds
    Deadline: the relative deadline of each task (second)
    ReleaseTimeDelay: the delay of first release time (second)
    RunningTime: the running time of tasks (second), 1s is a period.
    Dependencies: the dependencies of tasks
    Priority: the priority of tasks

    """
     # Load the handlers from the handler config file
    try:
        with open(task_config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("Error: Invalid JSON file")
        return
    
    # Check if the config file has a handler list
    if "task_list" not in config:
        print("Error: Missing `task_list` in config file")
        return
    
    # Check if the handler list is a list
    if not isinstance(config["task_list"], list):
        print("Error: `task_list` must be a list")
        return
    
    task_config = config["task_list"]
    
    # Validate the task_config
    try:
        validate_task_config(task_config)
    except ValueError as e:
        print(e)
    
    return task_config

def load_dag_config(dag_config_path):
    """
    Load a dag config from a JSON file.
    Task Configuration:
    {
        "dag_list": List<List<TaskConfigObject>>
    }

    TaskConfigObject Attributes:
    
    
    HandlerId: the handler id of tasks
    RunningTime: the running time of tasks (ms)
    Dependencies: the dependencies of tasks
    Priority: the priority of tasks
    RunArgs: SIMO run arguments
    WorstRunningTime: Wrost running time for this task (ms)

    """
     # Load the handlers from the handler config file
    try:
        with open(dag_config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("Error: Invalid JSON file")
        return
    
    # Check if the config file has a handler list
    if "dag_list" not in config:
        print("Error: Missing `task_list` in config file")
        return
    
    # Check if the handler list is a list
    if not isinstance(config["dag_list"], list):
        print("Error: `task_list` must be a list")
        return
    
    dag_config = config["dag_list"]
    running_time_factor = 1
    if("RunningTimeFactor" in config):
        running_time_factor = config["RunningTimeFactor"]
    
    return dag_config, running_time_factor

def generate_tasks(task_config):
    """
    Generate tasks queue from the task config.
    Task Attributes:

    TaskId: task id
    HandlerId: handler id
    ReleaseTime: The relative release time of task, depends on Period, ReleaseTimeDelay
    Deadline: The relative deadline of task, depends on Deadline, ReleaseTime and ReleaseTimeDelay
    Priority: task priority
    Dependencies: task dependencies, contains the handler id of tasks
    """
    tasks = []
    for config in task_config:
        gap = 1 / config["Period"]
        for each_period in range(config["RunningTime"]):
            start_time = config["ReleaseTimeDelay"] + each_period
            for i in range(config["Period"]):
                task = {
                    "TaskId": f"Period[{each_period}]_#{i}_Id[{config['HandlerId']}]_[{config['ReleaseTimeDelay']}]_{generate(size=7)}",
                    "HandlerId": config["HandlerId"],
                    "ReleaseTime": start_time + i * gap,
                    "Deadline": start_time + i * gap + config["Deadline"], # deadline won't extend for ReleaseTimeDelay
                    "Priority": config["Priority"],
                    "Dependencies": config["Dependencies"]
                }
                tasks.append(task)
    return tasks

def generate_tasks_from_dag(dag_config, time_factor=1):
    """
    Generate tasks queue from the task config.
    Task Attributes:

    TaskId: task id
    DagPeriod: the period time of DAG
    HandlerId: handler id
    ReleaseTime: The relative release time of task, depends on ReleaseTimeDelay and DagPeriod
    Deadline: The relative deadline of task, depends on Deadline, ReleaseTime and ReleaseTimeDelay
    Priority: task priority
    Dependencies: task dependencies, contains the handler id of tasks
    RunArgs: SIMO run arguments
    """
    tasks = []
    DagRepeatedTimes = 10
    start_time = 0
    def generate_task_obj(config, start_time, period):
        task = {
            "TaskId": f"{config['TaskName']}_[{period}]_{generate(size=7)}",
            "DagPeriod": i,
            "HandlerId": config["HandlerId"], # always 5
            "ReleaseTime": start_time / 1000,
            "Deadline": (start_time + config["WorstRunningTime"]*time_factor) / 1000, # deadline won't extend for ReleaseTimeDelay
            "Priority": config["Priority"],
            "Dependencies": config["Dependencies"],
            "RunArgs": str(config["RunArgs"]),
        }
        return task, config["WorstRunningTime"]*time_factor
    for dag in dag_config:
        for i in range(DagRepeatedTimes):
            for config in dag:                
                if(type(config) == list):
                    # for sub dag structure
                    parellel_running_time = 0
                    for subconfig in config:
                        task, running_time = generate_task_obj(subconfig, start_time, i)
                        # print('[debug] subconfig', task, start_time, i, subconfig['WorstRunningTime'])
                        tasks.append(task)
                        parellel_running_time += running_time
                    start_time += parellel_running_time
                else:
                    task, running_time = generate_task_obj(config, start_time, i)
                    tasks.append(task)
                    start_time += running_time
    return tasks


if __name__ == "__main__":
    dag_config, running_time_factor = load_dag_config("TaskConfigs/simo/agx_tight.json")
    tasks = generate_tasks_from_dag(dag_config, time_factor=running_time_factor)
    # print(tasks)
    assert(len(tasks) == 70)
