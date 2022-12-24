# this part is for directly running `python task1.py`
# if you don't have this condition, and only use task1.py as module in main.py, just `from AbstractHandler import AbstractHandler`
# because when you run `python main.py` in root dir, you can directly find `AbstractHandler.py`
if __name__ == '__main__':
    import sys
    sys.path.append('./')
    from AbstractHandler import AbstractHandler
else:
    from AbstractHandler import AbstractHandler

class task1(AbstractHandler):
    def run(self):
        print("run")
    
    def stop(self):
        print("stop")
    
    def load_data(self):
        print("load_data")
    
    def ready(self):
        print("ready")
    
    def exception(self):
        print("exception")
    
    def exit(self):
        print("exit")