import importlib, os, sys
AbstractDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
sys.path.append(AbstractDir)
AbstractHandlerModule = importlib.import_module("AbstractHandler")
AbstractHandler = getattr(AbstractHandlerModule, 'AbstractHandler')
HandlerStatus = getattr(AbstractHandlerModule, 'HandlerStatus')

AutoPilotModuleDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../Autopilot/')
sys.path.append(AutoPilotModuleDir)
Py_autopilot2_module = importlib.import_module("Py_autopilot2_module")
# if __name__ == "__main__":
#     import sys
#     sys.path.append('../')
#     from AbstractHandler import AbstractHandler
# else:
#     from AbstractHandler import AbstractHandler

import torch
import torchvision.transforms as transforms
import cv2
import matplotlib.pyplot as plt
import numpy as np
import math, asyncio
class handler6(AbstractHandler):
    def __init__(self, task_id, task_name, task_description):
        super().__init__(task_id, task_name, task_description)
        # 相对路径从根目录开始，因为handler的调用为根目录下的main.py
        # 测试时也从根目录调用文件, 如 python handler/handler1.py
        self.input_path = './Autopilot/img.jpg'
        self.width = 224
        self.height = 224
        self.model_path = './Autopilot/model_10000.pkl'
        self.BATCH = 1
    
    async def run(self, decoder_list=[]):
        try:
            return True
        except MemoryError:
            return "Memory Error in running task"
        except SystemError:
            return "System Error in running task"
        except ImportError as e:
            return f"Import errror in running task: {e}"
        except Exception as e:
            return f"Unexcepted Error: {e}"

        
    
    def stop(self):
        print("stop")
    

    async def load_data(self):
        return True
    
    def ready(self):
        print(f'I\'m ready {self.task_name}')
    
    def exception(self):
        print("exception")
    
    def exit(self):
        print("exit")

async def test():
    # test
    handler =  handler6(1, 'empty handler', 'description',  1, [])
    loop = asyncio.get_event_loop()
    load_data_task = loop.create_task(handler.load_data())
    await load_data_task
    run_task = loop.create_task(handler.run())
    output = await run_task
    print(f'Task completed with result: {output}')
    

if __name__ == "__main__":
    loop = asyncio.get_event_loop()    
    loop.run_until_complete(loop.create_task(test()))