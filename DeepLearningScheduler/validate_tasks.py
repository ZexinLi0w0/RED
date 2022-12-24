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

    unique_task_name = set()
    unique_task_id = set()
    # Validate the task attributes
    for i, task in enumerate(tasks):
        # Check if the task has all required attributes
        missing_attrs = []
        for attr in TaskAttributes:
            if attr not in task:
                missing_attrs.append(attr)
        if missing_attrs:
            raise ValueError(f"Invalid task #{i+1}: missing required attribute(s): {', '.join(missing_attrs)}")
        
        # check if the task_name and task_id is unique
        if(task["name"] in unique_task_name):
            raise ValueError(f"Task name must be unique in task id[{task['id']}]")
        if(task["id"] in unique_task_id):
            raise ValueError(f"Task id must be unique in task id[{task['id']}]")
        unique_task_name.add(task["name"])
        unique_task_id.add(task["id"])
        
        # Check if the dependencies attribute is a list
        if not isinstance(task["dependencies"], list):
            raise ValueError(f"Invalid task #{i+1}: dependencies must be a list in task id[{task['id']}]")
    
    # check dependencies of tasks are valid
    for i, task in enumerate(tasks):
        # Check if the dependencies are valid task IDs
        for dependency in task["dependencies"]:
            if dependency not in unique_task_id:
                raise ValueError(f"Invalid task #{i+1}: invalid dependency ID: {dependency} in task id[{task['id']}]")

if __name__ == "__main__":
    # add test cases
    pass