import re
import os

log_data = """2023-01-12 03:59:19,784 - INFO - [CTRL] Task S1_Stage3_Control_Autopilot_[1]_Nw9AP3_ finished, status: failure, start time: 0.7018845081329346, end time: 0.7522313594818115
2023-01-12 03:59:19,785 - INFO - [CTRL] Task S1_Stage1_LaneDetection_[2]_xWx7mZG finished, status: failure, start time: 0.7859480381011963, end time: 0.843346357345581
2023-01-12 03:59:19,838 - INFO - [CTRL] Task S1_Stage2_Segmentation_[2]_FGURhnw finished, status: failure, start time: 0.8513209819793701, end time: 0.903782844543457
2023-01-12 03:59:20,045 - INFO - [CTRL] Task S1_Stage3_Control_Autopilot_[2]_T4d_vyY finished, status: failure, start time: 0.977747917175293, end time: 1.0360798835754395
2023-01-12 03:59:20,222 - INFO - [CTRL] Task S1_Stage1_LaneDetection_[3]_b4KMlV6 finished, status: failure, start time: 1.1967053413391113, end time: 1.2508447170257568
"""

def parse_log(log_data):
    lines = log_data.split("\n")
    response_times = []
    for line in lines:
        if line:
            start_match = re.search("start time: (\d+\.\d+)", line)
            if start_match is None:
                continue
            start_time = float(start_match.group(1))
            # end_match = re.search("end time: (\d+\.\d+)", line)
            end_match = re.search("taskover time: (\d+\.\d+)", line)
            if end_match is None:
                continue
            end_time = float(end_match.group(1))
            response_time = end_time - start_time

            if response_time > 1:
                continue
            task_name = re.search("\[CTRL\] Task (.*?) finished", line).group(1)
            # print(f'Task: {task_name}, Response time: {response_time}')
            response_times.append(response_time)
    print(response_times)


if __name__ == "__main__":
    platform = 'tx2'
    files = os.listdir('./taskdata/{}_exp1/raw_data'.format(platform))
    for file in files:
        if file.__contains__('RED'):
            with open('./taskdata/{}_exp1/raw_data/{}'.format(platform, file), 'r') as f:
                print(file)
                log_data = f.read()
                parse_log(log_data)



