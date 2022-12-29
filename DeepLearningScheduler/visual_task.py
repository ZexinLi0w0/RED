import visdom
import numpy as np

"""
Before running this script, you need to install visdom first and launch a visdom server in another shell.

# Launch a visdom.server

Open a terminal, run `python -m visdom.server` (in your conda virtual env)
Pay attension to you 8097 port, it needs to be occupied by visdom.
"""
WindowName = 'TaskProgress'

vis = visdom.Visdom(env=WindowName)

def visual_task_blocks(tasks):    
    rows = []
    # max handler
    Y = []
    for i in range(5):
        rows.append([])
        Y.append('Handler' + str(i))
    Text = []    
    max_column = 0
    for task in tasks:
        # 获取 task 的开始时间和结束时间
        start = task['ReleaseTime']
        end = task['Deadline']
        # 获取 task 的 id
        _id = task['TaskId']
        handler_id = int(task["HandlerId"])
        # 将数据添加到 X，Y 和 Text 中
        rows[handler_id - 1].append(end - start) # bar length
        max_column = max(len(rows[handler_id - 1]), max_column)
        Text.append(_id)
    
    for r in rows:
        while(len(r) < max_column):
            r.append(0)

    # 将数据转化为 numpy 数组
    X = np.array(rows)
    Y = np.array(Y)
    # Text = np.array(Text)
    print(X.shape, Y.shape, len(Text))
    # print(X, Y, Text)

    # 使用 Visdom 画出块状图
    vis.bar(
        X=X,
        Y=Y,
        opts=dict(
            title = WindowName,
            width = 1000,
            height = 800,
            showlegend = True,
            xlabel = 'HandlerId',
            ylabel = 'TimeLine',
            ytick = True,
            ytickstep = 0.03,
            legend = Text,
            stacked = True            
        )
    )



if __name__ == "__main__":
    # test
    from task_generator import generate_tasks, load_task_config
    task_config = load_task_config("task-config.json")
    tasks = generate_tasks(task_config)
    visual_task_blocks(tasks)
