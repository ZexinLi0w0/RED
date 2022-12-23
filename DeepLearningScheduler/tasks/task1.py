import AbstractHandler

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
