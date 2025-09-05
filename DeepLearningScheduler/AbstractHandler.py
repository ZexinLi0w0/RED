from abc import ABC, abstractmethod
from enum import Enum
import asyncio

class HandlerStatus(Enum):
    Entry = "Entry"
    Load = "Load"
    Ready = "Ready"
    Running = "Running"
    Error = "Error"
    Exit = "Exit"

class AbstractHandler(ABC):
    def __init__(self, task_id, task_name, task_description):
        self._task_id = task_id
        self._task_name = task_name
        self._task_description = task_description
    
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
    class task(AbstractHandler):
        async def run(self):
            print("run")
        async def load_data(self):
            print("load_data")
        def stop(self):
            print("stop")
        def ready(self):
            print("ready")
        def exception(self):
            print("exception")
        def exit(self):
            print("exit")
    async def main():
        task1 = task(1, 'task1', 'task1')
        await task1.load_data()
        task1.ready()
        await task1.run()
        task1.exit()
    
    asyncio.run(main())
