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

### Task Config

Task Configuration:
```
{
    "task_list": List<TaskConfigObject>
}
```
TaskConfigObject Attributes:
```
HandlerId: the handler id of tasks
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
