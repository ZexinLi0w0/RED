from abc import ABC, abstractmethod

class AbstractHandler(ABC):
    def __init__(self, task_id, task_name, task_description, task_priority, task_dependencies, task_command, task_status):
        self._task_id = task_id
        self._task_name = task_name
        self._task_description = task_description
        self._task_priority = task_priority
        self._task_dependencies = task_dependencies
        self._task_command = task_command
        self._task_status = task_status
    
    @property
    def task_id(self):
        return self._task_id
    
    @task_id.setter
    def task_id(self, task_id):
        self._task_id = task_id

    @property
    def task_name(self):
        return self._task_name
    
    @task_name.setter
    def task_name(self, task_name):
        self._task_name = task_name
    
    @property
    def task_description(self):
        return self._task_description
    
    @task_description.setter
    def task_description(self, task_description):
        self._task_description = task_description
    
    @property
    def task_priority(self):
        return self._task_priority
    
    @task_priority.setter
    def task_priority(self, task_priority):
        self._task_priority = task_priority
    
    @property
    def task_dependencies(self):
        return self._task_dependencies
    
    @task_dependencies.setter
    def task_dependencies(self, task_dependencies):
        self._task_dependencies = task_dependencies
    
    @property
    def task_command(self):
        return self._task_command
    
    @task_command.setter
    def task_command(self, task_command):
        self._task_command = task_command
    
    @property
    def task_status(self):
        return self._task_status
    
    @task_status.setter
    def task_status(self, task_status):
        self._task_status = task_status

    @abstractmethod
    def run(self):
        pass
    
    @abstractmethod
    def stop(self):
        pass
    
    @abstractmethod
    def load_data(self):
        pass
    
    @abstractmethod
    def ready(self):
        pass
    
    @abstractmethod
    def exception(self):
        pass
    
    @abstractmethod
    def exit(self):
        pass

if __name__=="__main__":
    # test
    pass
    # class task(AbstractHandler):
    #     def run(self):
    #         print("run")
    #     def stop(self):
    #         print("stop")
    #     def load_data(self):
    #         print("load_data")
    #     def ready(self):
    #         print("ready")
    #     def exception(self):
    #         print("exception")
    #     def exit(self):
    #         print("exit")
    # task1 = task(1, 'task1', 'task1', 1, [], 'l')
    # task1.load_data()
    # task1.ready()
    # task1.run()
    # task1.exit()
