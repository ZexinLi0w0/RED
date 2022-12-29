import json

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

def generate_tasks(task_config):
    """
    Generate tasks queue from the task config.
    Task Attributes:

    ReleaseTime: The relative release time of task, depends on Period, ReleaseTimeDelay
    Deadline: The relative deadline of taks, depends on Deadline, ReleaseTime and ReleaseTimeDelay
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
                    "TaskId": f"Period[{each_period}]_#{i}_Id[{config['HandlerId']}]",
                    "HandlerId": config["HandlerId"],
                    "ReleaseTime": start_time + i * gap,
                    "Deadline": config["Deadline"] + i * gap + each_period, # deadline won't extend for ReleaseTimeDelay
                    "Priority": config["Priority"],
                    "Dependencies": config["Dependencies"]
                }
                tasks.append(task)
    return tasks


if __name__ == "__main__":
    task_config = load_task_config("task-config.json")
    tasks = generate_tasks(task_config)
    assert(len(tasks) == 300)
