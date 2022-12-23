# Deeplearing Scheduler

This is a scheduler to run and manage deep learning task.

Every task should implement `handlerAbstract.Handler` which is an Abstract Class.

Set a config file like `task-config.json` as input for `main.py` to start tasks.

Here is the finite state machine of a task
![](./docs/FSM.png)

### Autopilot Task

```shell
python \"./autopilotTask/test.py\" -width 100 -height 100 -input \"./autopilotTask/img.jpg\" --debug=True
```