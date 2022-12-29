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
class handler1(AbstractHandler):
    def __init__(self, task_id, task_name, task_description):
        super().__init__(task_id, task_name, task_description)
        # 相对路径从根目录开始，因为handler的调用为根目录下的main.py
        # 测试时也从根目录调用文件, 如 python handler/handler1.py
        self.input_path = './Autopilot/img.jpg'
        self.width = 100
        self.height = 100
        self.model_path = './Autopilot/model_10000.pkl'
        self.BATCH = 256
    
    async def run(self):
        try:
            output_list = []
            for i in range(self.BATCH):
                net_out = self.test_net.forward(self.data_input).squeeze().float() 
                steer_pred_angle = net_out.detach().cpu().numpy() / math.pi * 180
                output_list.append(steer_pred_angle)
            return output_list
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
        transform = transforms.Compose([
        transforms.ToTensor(),               ## shape:(31784, 100, 100, 3) -->(31784, 3,100, 100)
        transforms.Normalize((0.43567735,0.49298695,0.5192303), (0.22272868,0.24110594,0.29045662))     
        ])
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        img = np.array(cv2.resize((cv2.cvtColor(plt.imread(self.input_path), cv2.COLOR_RGB2HSV)), (self.width, self.height)), dtype=np.float32)
        data_input = transform(img).unsqueeze(0)
        #load network
        test_net = torch.load(self.model_path)
        test_net.eval()
        data_input = data_input.to(device)
        test_net = test_net.to(device)
        self.data_input = data_input
        self.test_net = test_net
        return {
            "data_input": data_input,
            "network": test_net,
        }
    
    def ready(self):
        print('I\'m ready')
    
    def exception(self):
        print("exception")
    
    def exit(self):
        print("exit")

async def test():
    # test
    handler =  handler1(1, 'autopilot', 'description',  1, [])
    loop = asyncio.get_event_loop()
    load_data_task = loop.create_task(handler.load_data())
    await load_data_task
    run_task = loop.create_task(handler.run())
    output = await run_task
    print(f'Task completed with result: {output}')
    

if __name__ == "__main__":
    loop = asyncio.get_event_loop()    
    loop.run_until_complete(loop.create_task(test()))