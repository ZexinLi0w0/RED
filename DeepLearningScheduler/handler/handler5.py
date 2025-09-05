import importlib, os, sys
AbstractDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
sys.path.append(AbstractDir)
AbstractHandlerModule = importlib.import_module("AbstractHandler")
AbstractHandler = getattr(AbstractHandlerModule, 'AbstractHandler')
HandlerStatus = getattr(AbstractHandlerModule, 'HandlerStatus')

SIMODir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../SIMO/')
sys.path.append(SIMODir)
SIMONet = importlib.import_module("SIMONet").SIMONet
# if __name__ == "__main__":
#     import sys
#     sys.path.append('../')
#     from AbstractHandler import AbstractHandler
# else:
#     from AbstractHandler import AbstractHandler

import torch
import torch.nn as nn
import torch.nn.functional as F
import argparse
import sys
import glob
import cv2
import numpy as np
import time
import asyncio
import profile

from loss import DiscriminativeLoss
# from backbone.UNet import UNet_Encoder, UNet_Decoder
from backbone.ENet import ENet_Encoder, ENet_Decoder
from backbone.MLP import MLP_Decoder
from backbone.Segmentation import Segmentation_Decoder
from backbone.ObjectDetection import ObjectDetection_Decoder

# from backbone.deeplabv3_plus.deeplabv3plus import Deeplabv3plus_Encoder, Deeplabv3plus_Decoder

from utils.general import non_max_suppression, scale_coords


class handler5(AbstractHandler):
    def __init__(self, task_id, task_name, task_description):
        super().__init__(task_id, task_name, task_description)
        # 相对路径从根目录开始，因为handler的调用为根目录下的main.py
        # 测试时也从根目录调用文件, 如 python handler/handler1.py
        self.width = 224
        self.height = 224
        self.BATCH = 1
        
    
    async def run(self, decoder_list=[1,2,3,4]):
        model = self.model
        input_img = self.input_img
        try:
            output_list = []
            for i in range(self.BATCH):
                net_out = model.forward(input_img, decoder_list)
                output_list.append(net_out)
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
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        device = self.device
        input_img = torch.randn(1, 3, self.width, self.height).to(device)
        model = SIMONet().to(device)
        self.input_img = input_img
        self.model = model
    
    def ready(self):
        print(f'I\'m ready {self.task_name}')
    
    def exception(self):
        print("exception")
    
    def exit(self):
        print("exit")

async def test():
    # test
    handler =  handler5(7, 'SIMO', 'description')
    loop = asyncio.get_event_loop()
    load_data_task = loop.create_task(handler.load_data())
    await load_data_task
    run_task = loop.create_task(handler.run())
    output = await run_task
    print(f'Task completed with result: {output}')
    

if __name__ == "__main__":
    loop = asyncio.get_event_loop()    
    loop.run_until_complete(loop.create_task(test()))