# Deeplearing Scheduler

This is a scheduler to run and manage deep learning task.

Every task should implement `handlerAbstract.Handler` which is an Abstract Class.

Set a config file like `handler-config.json` as input for `main.py` to start a handler to run tasks.

Here is the finite state machine of a handler
![](./docs/FSM.png)

### Run a scheduler to start some tasks

```shell
python "./main.py" -c handler-config.json
```

### Test a handler

```shell
python "./handler/handler1.py"
```

### Autopilot Task

```shell
python "./Autopilot/test.py" -width 100 -height 100 -input "./Autopilot/img.jpg" --debug=True
```
