import importlib, os, sys
AbstractDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
sys.path.append(AbstractDir)
AbstractHandlerModule = importlib.import_module("AbstractHandler")
AbstractHandler = getattr(AbstractHandlerModule, 'AbstractHandler')
HandlerStatus = getattr(AbstractHandlerModule, 'HandlerStatus')

SegmentationModuleDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../Pytorch-UNet/')
sys.path.append(SegmentationModuleDir)
SegmentationModule = importlib.import_module("unet")
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
import math, time, asyncio

    

avgtime = {}
def time_avg(key='task'):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            elapsed = end - start
            if(key not in avgtime):
                avgtime[key] = {"total": 0, "count": 0}
            avgtime[key]["total"] += elapsed
            avgtime[key]["count"] += 1
            return result
        return wrapper
    return decorator

def time_it(output=''):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            elapsed = end - start
            print(output, elapsed, 's')
            return result
        return wrapper
    return decorator

class handler2(AbstractHandler):
    def __init__(self, task_id, task_name, task_description, task_priority, task_dependencies):
        super().__init__(task_id, task_name, task_description, task_priority, task_dependencies)
        # 相对路径从根目录开始，因为handler的调用为根目录下的main.py
        # 测试时也从根目录调用文件, 如 python handler/handler2.py
        self.input_path = './Autopilot/img.jpg'
        self.width = 100
        self.height = 100
        self.model_path = '../Pytorch-UNet/unet_carvana_scale1.0_epoch2.pth'
        self.BATCH = 256
    
    # @time_it('[Metrics][TIME] Running: ')
    async def run(self):
        try:
            for i in range(self.BATCH):
                net_out = self.test_net(self.data_input)
            return net_out.shape
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
    
    # @time_it('[Metrics][TIME] Load Data: ')
    async def load_data(self):
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5,0.5,0.5), (0.5,0.5,0.5)),
            transforms.Resize((self.width, self.height))
        ])
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

        raw_img = cv2.imread(self.input_path)
        img = transform(raw_img)
        img = img.unsqueeze(0)
        img = img.to(device)

        net = SegmentationModule.UNet(n_channels=3, n_classes=2, bilinear=False)
        net.load_state_dict(torch.load(self.model_path, map_location=device))
        net.to(device=device)

        self.data_input = img
        self.test_net = net

        return {
            "data_input": img,
            "network": net,
        }
    
    def ready(self):
        print('I\'m ready')
    
    def exception(self):
        print("exception")
    
    def exit(self):
        print("exit")

async def test():
    # test
    handler =  handler2(1, 'segmentation', 'description',  1, [])
    loop = asyncio.get_event_loop()
    load_data_task = loop.create_task(handler.load_data())
    await load_data_task
    run_task = loop.create_task(handler.run())
    output = await run_task
    print(f'Task completed with result: {output}')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(loop.create_task(test()))