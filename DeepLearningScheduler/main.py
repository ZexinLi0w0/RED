import argparse
import json
from multiprocessing import Queue, freeze_support, set_start_method
import importlib
import asyncio


# required attributes in config file
TaskAttributes = ["id", "name", "description", "priority", "dependencies", "run"]

def validate_tasks(tasks):
    """
    Function to validate the tasks in the task list.
    """
    # def check_dependencies(task_id, visited):
    #     """
    #     Recursive function to check if the task dependencies have a circular reference.
    #     """
    #     task = next((t for t in tasks if t["id"] == task_id), None)
    #     if task is None:
    #         return
    #     if task["id"] in visited:
    #         raise ValueError(f"Invalid task #{task['id']}: circular dependencies found")
    #     visited.add(task["id"])
    #     for dependency in task["dependencies"]:
    #         check_dependencies(dependency, visited)
    # Validate the task attributes
    for i, task in enumerate(tasks):
        # Check if the task has all required attributes
        missing_attrs = []
        for attr in TaskAttributes:
            if attr not in task:
                missing_attrs.append(attr)
        if missing_attrs:
            raise ValueError(f"Invalid task #{i+1}: missing required attribute(s): {', '.join(missing_attrs)}")

        # Check if the dependencies attribute is a list
        if not isinstance(task["dependencies"], list):
            raise ValueError(f"Invalid task #{i+1}: dependencies must be a list")

        # Check if the dependencies are valid task IDs
        for dependency in task["dependencies"]:
            if dependency not in [t["id"] for t in tasks]:
                raise ValueError(f"Invalid task #{i+1}: invalid dependency ID: {dependency}")

async def handle_signaling(control_queue):
    while True:
        sig = control_queue.get()
        print('receiving signal from sub process:', sig)

def create_task(task_id, task_name, task_description, task_priority, task_dependencies, task_command):
    """
    Function to run a single task.
    """
    print(f"Running task {task_id}: {task_name}")
    # Run the task command
    task_file_name = f"task{task_id}"
    task_module = importlib.import_module(f'./tasks/{task_file_name}')
    TaskConcreteClass = getattr(task_module, task_file_name)
    task = TaskConcreteClass(task_id, task_name,  task_description, task_priority, task_dependencies, task_command)

    # handler.run()

def run_tasks(tasks, control_queue):
    """
    Function to run tasks concurrently.
    """
    # Create a list of processes
    processes = []
    for task in tasks:
        task_id = task["id"]
        task_name = task["name"]
        task_description = task["description"]
        task_priority = task["priority"]
        task_dependencies = task["dependencies"]
        task_command = task["run"]

        # Create a process for each task
        process = Process(target=create_task, args=(task_id, task_name, task_description, task_priority, task_dependencies, task_command))
        processes.append(process)

    # Start all processes
    for process in processes:
        process.start()

    loop = asyncio.get_event_loop()
    handle_signaling_task = loop.create_task(handle_signaling(control_queue))
    try:
        loop.run_until_complete(handle_signaling_task)
    except KeyboardInterrupt:
        print('[CLOSE] KeyboardInterrupt, close all tasks and loop')
    finally:
        for process in processes:
            process.terminate()
        loop.stop()
        loop.close()

    # Continuously check the queue for control signals
    # while True:
    #     # Check if there is a control signal in the queue
    #     try:
    #         control_signal = queue.get_nowait()
    #     except queue.Empty:
    #         # No control signal, continue checking
    #         continue
    #     else:
    #         if control_signal == "exception":
    #             # Stop all processes
    #             for process in processes:
    #                 process.terminate()
    #             break
    #         elif control_signal == "pause":
    #             # Pause all processes
    #             for process in processes:
    #                 process.suspend()
    #         elif control_signal == "resume":
    #             # Resume all processes
    #             for process in processes:
    #                 process.resume()

def parserHandler():
    """
    Function to parse the command line arguments.
    Validate the task config file.
    Run the tasks.
    """
     # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--input", "-i", required=True, help="path of input task config file")
    parser.add_argument("--generate", "-g", required=False, help="path of tasks folder to automatically infer the task config file")
    args = parser.parse_args()

    # Load the tasks from the task config file
    try:
        with open(args.input, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("Error: Invalid JSON file")
        return
    
    # Check if the config file has a task list
    if "tasklist" not in config:
        print("Error: Missing `tasklist` in config file")
        return
    
    # Check if the task list is a list
    if not isinstance(config["tasklist"], list):
        print("Error: `tasklist` must be a list")
        return
    
    tasks = config["tasklist"]
    
    # Validate the tasks
    try:
        validate_tasks(tasks)
    except ValueError as e:
        print(e)
    
    return tasks
    

if __name__ == "__main__":
    tasks = parserHandler()
    freeze_support()
    # Set the start method to spawn, The child process will only inherit those resources necessary to run the process object's run() method
    set_start_method('spawn')
    # Create a queue for control signals
    control_queue = Queue()

    # Start the tasks concurrently
    run_tasks(tasks, control_queue)