"""Moving-average cost estimation and residual-DAG deadline reassignment."""

from collections import defaultdict, deque


DEFAULT_MOVING_AVERAGE_WINDOW = 8


def _positive_integer(value, field_name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def execution_profile_key(task):
    """Return a period-independent identity for one scheduling node profile."""
    run_args = task.get("RunArgs", [])
    if isinstance(run_args, str):
        outputs = tuple(
            sorted(
                int(value)
                for value in run_args.strip("[").strip("]").split(",")
                if value.strip()
            )
        )
    else:
        outputs = tuple(sorted(int(value) for value in run_args))
    return (
        task.get("DagIndex"),
        task.get("StageIndex"),
        int(task.get("HandlerId", -1)),
        outputs,
    )


def dag_instance_key(task):
    """Return the released DAG instance that owns ``task``."""
    if task.get("DagIndex") is None or task.get("DagPeriod") is None:
        return None
    return (int(task["DagIndex"]), int(task["DagPeriod"]))


class MovingAverageCostEstimator:
    """Estimate node costs from the most recent configured observations."""

    def __init__(self, window=DEFAULT_MOVING_AVERAGE_WINDOW):
        self.window = _positive_integer(window, "MovingAverageWindow")
        self._history = defaultdict(lambda: deque(maxlen=self.window))

    def observe(self, task, duration_seconds):
        duration_seconds = float(duration_seconds)
        if duration_seconds <= 0:
            raise ValueError("observed execution duration must be positive")
        key = execution_profile_key(task)
        self._history[key].append(duration_seconds)
        return self.estimate(task)

    def estimate(self, task):
        history = self._history.get(execution_profile_key(task))
        if history:
            return sum(history) / len(history)
        fallback = float(task["EstimatedExecutionTime"])
        if fallback <= 0:
            raise ValueError("EstimatedExecutionTime must be positive")
        return fallback

    def observations(self, task):
        return list(self._history.get(execution_profile_key(task), ()))


def proportional_residual_deadlines(
    tasks,
    now_seconds,
    absolute_end_to_end_deadline,
    cost_estimator,
):
    """Assign cumulative deadlines to remaining levels of one DAG instance.

    The assignment follows the manuscript's proportional rule: the remaining
    end-to-end budget is divided by the sum of estimated costs at each remaining
    scheduling level. Every node at one level receives the same cumulative
    absolute deadline. No averaging is applied to reported experiment metrics;
    the moving average is used only as the online execution-cost estimate.
    """
    tasks = list(tasks)
    if not tasks:
        return {}

    now_seconds = float(now_seconds)
    absolute_end_to_end_deadline = float(absolute_end_to_end_deadline)
    levels = defaultdict(list)
    for task in tasks:
        if "StageIndex" not in task:
            raise ValueError("residual DAG tasks must define StageIndex")
        levels[int(task["StageIndex"])].append(task)

    level_costs = {
        level: sum(float(cost_estimator(task)) for task in level_tasks)
        for level, level_tasks in levels.items()
    }
    total_cost = sum(level_costs.values())
    if total_cost <= 0:
        raise ValueError("residual estimated execution cost must be positive")

    remaining_budget = max(0.0, absolute_end_to_end_deadline - now_seconds)
    cumulative_cost = 0.0
    assignments = {}
    for level in sorted(levels):
        cumulative_cost += level_costs[level]
        deadline = now_seconds + remaining_budget * cumulative_cost / total_cost
        for task in levels[level]:
            assignments[task["TaskId"]] = min(
                deadline, absolute_end_to_end_deadline
            )
    return assignments
