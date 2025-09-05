# Deeplearing Scheduler

This is a scheduler to run and manage deep learning task.

Every task should implement `handlerAbstract.Handler` which is an Abstract Class.

Set a config file like `handler-config.json` as input for `main.py` to start a handler to run tasks.

Here is the finite state machine of a handler
![](./docs/FSM.png)

### Run a scheduler to start some tasks

```shell
python "./main.py" -c handler-config.json -t task-config.json
```

### Handler Config

> Each handler can be assigned several tasks by the controller.
> 
> Each handler should implement `AbstractHandler` with `run`, `load_data`, `ready`, `exception`, `exit` methods.

```
{
    "handler_list": List<HandlerConfigObject>
    "handler_dir": string, // the custom handlers directory, default "handler"
}
```

HandlerConfigObject

```
id: handler_id, the default path of handler module will be './handler/handler{id}.py'
name: handler name
description: handler description
```

### Task Config

> This config file is to describe the tasks you want to run on handlers.
> 
> Like how many seconds of the total running time, how many fps you want for a task.

Task Configuration:
```
{
    "task_list": List<TaskConfigObject>
}
```
TaskConfigObject Attributes:
```
HandlerId: the handler id of tasks to be assigned.
Period: the amount of each task per 1 second, e.g. 30(fps) mean 30 tasks per 1 seconds
Deadline: the relative deadline of each task (second)
ReleaseTimeDelay: the delay of first release time (second)
RunningTime: the running time of tasks (second), 1s is a period.
Dependencies: the dependencies of tasks
Priority: the priority of tasks
```


### Test a handler

```shell
python "./handler/handler1.py"
```

### Autopilot Task

```shell
python "./Autopilot/test.py" -width 100 -height 100 -input "./Autopilot/img.jpg" --debug=True
```


## SIMO Experiement

### Baseline
```
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo-baseline-nano.json" -a "baseline"

# agx loose
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose.json" -a "baseline"

# agx tight
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_tight.json" -a "baseline"

# tx2 loose
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/tx2_loose.json" -a "baseline"

# tx2 tight
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/tx2_tight.json" -a "baseline"
```

### Task Progress Tracker(Execution Feedback to adjust release time)
```
python main.py -c "./handler-config.json" -t "./TaskConfigs/simo-baseline-nano.json" -a "feedback"

# agx loose
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose.json" -a "feedback"

# agx tight
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_tight.json" -a "feedback"


```

### Fine Grained
```
python main.py -c "./handler-config.json" -t "./TaskConfigs/simo-baseline-nano.json" -a "fine-grained"

# agx loose
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose.json" -a "fine-grained"

# agx tight
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_tight.json" -a "fine-grained"
```

### Progress Tracker + Fine Grained Combination
```
python main.py -c "./handler-config.json" -t "./TaskConfigs/simo-baseline-nano.json" -a "feedback-fine-grained"

# agx loose
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_loose.json" -a "feedback-fine-grained"

# agx tight
python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/agx_tight.json" -a "feedback-fine-grained"
```

### Enable Skip Mode

Only Progress Tracker + Fine Grained Combination approach will enable skip mode.

But you can enable it manually.

Add --skipmode for signal_message in `control_signal.py`

Comment line 50 and uncomment <b>the 52nd line</b>


### Overhead measurement

```
python main.py -c "./overhead-handler.json" -t "./TaskConfigs/overhead-measure.json" -a "feedback"
```

### Clean taskdata without rename
```shell
rm taskdata/statistics_*
```