import argparse
import torch
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import cv2
import matplotlib.pyplot as plt
import numpy as np
import math, time

import sys
sys.path.append('./Autopilot/')
# self-defined module
import Py_autopilot2_module

debug = False

def time_it(output=''):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            elapsed = end - start
            debug and print(output, elapsed, 's')
            return result
        return wrapper
    return decorator

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


@time_it('[Metrics][TIME] Load Data: ')
def load(model_path, input_path, height, width):
    transform = transforms.Compose([
        transforms.ToTensor(),               ## shape:(31784, 100, 100, 3) -->(31784, 3,100, 100)
        transforms.Normalize((0.43567735,0.49298695,0.5192303), (0.22272868,0.24110594,0.29045662))     
    ])
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    img = np.array(cv2.resize((cv2.cvtColor(plt.imread(input_path), cv2.COLOR_RGB2HSV)), (width, height)), dtype=np.float32)
    data_input = transform(img).unsqueeze(0)
    #load network
    test_net = torch.load(model_path)
    test_net.eval()
    data_input = data_input.to(device)
    test_net = test_net.to(device)
    return {
        "data_input": data_input,
        "network": test_net,
    }

@time_it('[Metrics][TIME] Running: ')
def test(input_data, network):
    # import pdb; pdb.set_trace()
    net_out = network.forward(input_data).squeeze().float() 
    debug and print('Predicted output:', net_out.detach().cpu().numpy())
    steer_pred_angle = net_out.detach().cpu().numpy() / math.pi * 180
    return steer_pred_angle
    
def main():
    global debug
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(add_help=True)

    # 添加命令行参数
    parser.add_argument('--input_data_path', '-input', required=True, help='input data path')
    parser.add_argument('--input_height', '-height', required=True, type=int, help='input image height')
    parser.add_argument('--input_width', '-width', required=True, type=int, help='input image width')
    parser.add_argument('--batch', '-b', required=True, type=int, help='batch size')
    parser.add_argument('--debug', required=False, type=bool, help='set debug mode')
    
    # 解析命令行参数
    args = parser.parse_args()

    # 获取命令行参数的值
    model_path = './Autopilot/model_10000.pkl'
    input_path = args.input_data_path
    height = args.input_height
    width = args.input_width
    batch = args.batch or 1
    debug = args.debug


    # load data
    loadres = load(model_path, input_path, height, width)
    dataloader = loadres["data_input"]
    network = loadres["network"]
    # run model test
    for i in range(batch):  
        res = test(dataloader, network)
    
    # debug and print("Predicted steering angle: ", res)
    return res


if __name__ == '__main__':
    res = main()
