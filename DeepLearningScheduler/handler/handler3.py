import importlib, os, sys

AbstractDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
sys.path.append(AbstractDir)
AbstractHandlerModule = importlib.import_module("AbstractHandler")
AbstractHandler = getattr(AbstractHandlerModule, 'AbstractHandler')
HandlerStatus = getattr(AbstractHandlerModule, 'HandlerStatus')

LaneDetectionModuleDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lanenet-lane-detection-pytorch/')
sys.path.append(LaneDetectionModuleDir)
LaneDetectionModule = importlib.import_module("model.lanenet.LaneNet")

import torch
import torchvision.transforms as transforms
import cv2
import matplotlib.pyplot as plt
import numpy as np
import math, time, asyncio

class handler3(AbstractHandler):
    def __init__(self, task_id, task_name, task_description):
        super().__init__(task_id, task_name, task_description)
        # 相对路径从根目录开始，因为handler的调用为根目录下的main.py
        # 测试时也从根目录调用文件, 如 python handler/handler3.py
        self.input_path = './Autopilot/img.jpg'
        self.width = 224
        self.height = 224
        self.model_path = './lanenet-lane-detection-pytorch/log/best_model.pth'
        self.BATCH = 1
    
    async def run(self):
        try:
            for i in range(self.BATCH):
                net_out = self.test_net(self.data_input)
            return {
                "instance_seg_logits": net_out['instance_seg_logits'].shape,
                "binary_seg_logits": net_out['binary_seg_logits'].shape,
                "binary_seg_pred": net_out['binary_seg_pred'].shape,
            }
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
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.Resize((self.width, self.height))
        ])
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

        raw_img = cv2.imread(self.input_path)
        img = transform(raw_img)
        img = img.unsqueeze(0)
        img = img.to(device)

        net = LaneDetectionModule.LaneNet(arch="ENet")
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
    handler = handler3(1, 'lanedetection', 'description', 1, [])
    loop = asyncio.get_event_loop()
    load_data_task = loop.create_task(handler.load_data())
    await load_data_task
    run_task = loop.create_task(handler.run())
    output = await run_task
    print(f'Task completed with result: {output}')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(loop.create_task(test()))