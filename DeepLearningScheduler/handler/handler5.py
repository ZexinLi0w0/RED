import importlib, os, sys
import torch
import torchvision.transforms as transforms
import asyncio
import cv2

# import AbstractHandler
AbstractDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
sys.path.append(AbstractDir)
AbstractHandlerModule = importlib.import_module("AbstractHandler")
AbstractHandler = getattr(AbstractHandlerModule, 'AbstractHandler')
HandlerStatus = getattr(AbstractHandlerModule, 'HandlerStatus')


class handler5(AbstractHandler):
    """
    Yolov5 Handler
    """
    def __init__(self, task_id, task_name, task_description):
        super().__init__(task_id, task_name, task_description)
        # 相对路径从根目录开始，因为handler的调用为根目录下的main.py
        # 测试时也从根目录调用文件, 如 python handler/handler1.py
        self.input_path = './Autopilot/img2.jpg'
        self.width = 100
        self.height = 100
        self.BATCH = 2
    
    async def run(self):
        try:
            output_list = []
            for i in range(self.BATCH):
                results = self.test_net(self.data_input)
                results.print()
                output_list.append(results)
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
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.Resize((self.width, self.height))
        ])
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        test_net = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        test_net = test_net.to(device)
        data_input = cv2.imread(self.input_path)
        data_input = transform(data_input)
        data_input = data_input.unsqueeze(0)
        data_input = data_input.to(device)
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
    handler =  handler5(1, 'yolov5', 'run a yolov5 inference as documents',  1, [])
    loop = asyncio.get_event_loop()
    load_data_task = loop.create_task(handler.load_data())
    await load_data_task
    run_task = loop.create_task(handler.run())
    output = await run_task
    print(f'Task completed with result: {output}')
    

if __name__ == "__main__":
    loop = asyncio.get_event_loop()    
    loop.run_until_complete(loop.create_task(test()))