import json
import hashlib
from dataclasses import dataclass

from nanoid import generate

# Required Attributes for TaskConfigObject
TaskConfigAttributes = ["HandlerId", "Period", "Deadline", "RunningTime", "Priority", "Dependencies"]

# Optional Attributes for Burst Task Support
BurstTaskAttributes = ["BurstPriority", "CriticalityWeight", "DropThreshold"]


@dataclass(frozen=True)
class DagTimingConfig:
    """Timing controls for generated DAG instances.

    ``deadline_factor`` scales each node's relative deadline budget, while
    ``arrival_scale`` independently scales the nominal release timeline.
    Parallel stages follow the application-DAG critical path by default.
    """

    deadline_factor: float = 1.0
    arrival_scale: float = 1.0
    dag_repeated_times: int = 10
    parallel_stage_policy: str = "max"
    task_seed: int = 0
    merge_threshold_ms: float = 20.0


def _positive_number(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return float(value)


def timing_config_from_mapping(config):
    """Parse explicit timing controls, with a compatibility path for old JSON."""
    has_legacy_factor = "RunningTimeFactor" in config
    explicit_fields = {"DeadlineFactor", "ArrivalScale"}
    present_explicit_fields = explicit_fields.intersection(config)

    if has_legacy_factor and present_explicit_fields:
        raise ValueError(
            "RunningTimeFactor cannot be combined with DeadlineFactor or ArrivalScale"
        )
    if present_explicit_fields and present_explicit_fields != explicit_fields:
        missing = sorted(explicit_fields - present_explicit_fields)
        raise ValueError(
            "split timing configuration requires both DeadlineFactor and "
            f"ArrivalScale; missing {missing}"
        )

    if has_legacy_factor:
        legacy_factor = _positive_number(
            config["RunningTimeFactor"], "RunningTimeFactor"
        )
        deadline_factor = legacy_factor
        arrival_scale = legacy_factor
    elif present_explicit_fields:
        deadline_factor = _positive_number(
            config["DeadlineFactor"], "DeadlineFactor"
        )
        arrival_scale = _positive_number(config["ArrivalScale"], "ArrivalScale")
    else:
        deadline_factor = 1.0
        arrival_scale = 1.0

    dag_repeated_times = config.get("DagRepeatedTimes", 10)
    if (
        isinstance(dag_repeated_times, bool)
        or not isinstance(dag_repeated_times, int)
        or dag_repeated_times <= 0
    ):
        raise ValueError("DagRepeatedTimes must be a positive integer")

    parallel_stage_policy = config.get("ParallelStagePolicy", "max")
    if parallel_stage_policy not in {"max", "sum"}:
        raise ValueError("ParallelStagePolicy must be either 'max' or 'sum'")

    task_seed = config.get("TaskSeed", 0)
    if isinstance(task_seed, bool) or not isinstance(task_seed, int) or task_seed < 0:
        raise ValueError("TaskSeed must be a non-negative integer")

    merge_threshold_ms = config.get("MergeThresholdMs", 20.0)
    if (
        isinstance(merge_threshold_ms, bool)
        or not isinstance(merge_threshold_ms, (int, float))
        or merge_threshold_ms < 0
    ):
        raise ValueError("MergeThresholdMs must be a non-negative number")

    return DagTimingConfig(
        deadline_factor=deadline_factor,
        arrival_scale=arrival_scale,
        dag_repeated_times=dag_repeated_times,
        parallel_stage_policy=parallel_stage_policy,
        task_seed=task_seed,
        merge_threshold_ms=float(merge_threshold_ms),
    )

def validate_task_config(task_config):
    """
    Function to validate the task configs.
    """
    # Validate the task attributes
    for i, task in enumerate(task_config):
        # Check if the task has all required attributes
        missing_attrs = []
        for attr in TaskConfigAttributes:
            if attr not in task:
                missing_attrs.append(attr)
        if missing_attrs:
            raise ValueError(f"Invalid task #{i+1}: missing required attribute(s): {', '.join(missing_attrs)}")
        
        # Check if the dependencies attribute is a list
        if not isinstance(task["Dependencies"], list):
            raise ValueError(f"Invalid task #{i+1}: Dependencies must be a list in task id[{task['HandlerId']}]")
        if not isinstance(task["Priority"], int):
            raise ValueError(f"Invalid task #{i+1}: Priority must be an int in task id[{task['HandlerId']}]")
        if not isinstance(task["Deadline"], float):
            raise ValueError(f"Invalid task #{i+1}: Deadline must be a float in task id[{task['HandlerId']}]")
        if not isinstance(task["Period"], int):
            raise ValueError(f"Invalid task #{i+1}: Period must be an int in task id[{task['HandlerId']}]")
        if not isinstance(task["RunningTime"], int):
            raise ValueError(f"Invalid task #{i+1}: RunningTime must be an int in task id[{task['HandlerId']}]")
        if "ReleaseTimeDelay" in task:
            if not isinstance(task["ReleaseTimeDelay"], float) and not isinstance(task["ReleaseTimeDelay"], int):
                raise ValueError(f"Invalid task #{i+1}: ReleaseTimeDelay must be a float in task id[{task['HandlerId']}]")
        else:
            task["ReleaseTimeDelay"] = 0.0

def load_task_config(task_config_path):
    """
    Load a task config from a JSON file.
    Task Configuration:
    {
        "task_list": List<TaskConfigObject>
    }

    TaskConfigObject Attributes:

    HandlerId: the handler id of tasks
    Period: the amount of each task per 1 second, e.g. 30(fps) mean 30 tasks per 1 seconds
    Deadline: the relative deadline of each task (second)
    ReleaseTimeDelay: the delay of first release time (second)
    RunningTime: the running time of tasks (second), 1s is a period.
    Dependencies: the dependencies of tasks
    Priority: the priority of tasks

    """
     # Load the handlers from the handler config file
    try:
        with open(task_config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("Error: Invalid JSON file")
        return
    
    # Check if the config file has a handler list
    if "task_list" not in config:
        print("Error: Missing `task_list` in config file")
        return
    
    # Check if the handler list is a list
    if not isinstance(config["task_list"], list):
        print("Error: `task_list` must be a list")
        return
    
    task_config = config["task_list"]
    
    # Validate the task_config
    try:
        validate_task_config(task_config)
    except ValueError as e:
        print(e)
    
    return task_config

def _load_dag_config_mapping(dag_config_path):
    try:
        with open(dag_config_path, "r") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in DAG config {dag_config_path}") from exc

    if "dag_list" not in config:
        raise ValueError("missing `dag_list` in DAG config")
    if not isinstance(config["dag_list"], list):
        raise ValueError("`dag_list` must be a list")

    return config


def _non_partitionable_config_from_mapping(config):
    non_partitionable_percentage = config.get("NonPartitionablePercentage", 0)
    if (
        isinstance(non_partitionable_percentage, bool)
        or not isinstance(non_partitionable_percentage, (int, float))
        or not 0 <= non_partitionable_percentage <= 100
    ):
        raise ValueError("NonPartitionablePercentage must be between 0 and 100")

    non_partitionable_config = config.get("NonPartitionableConfig")
    if non_partitionable_config is not None and not isinstance(
        non_partitionable_config, dict
    ):
        raise ValueError("NonPartitionableConfig must be a dictionary")

    return float(non_partitionable_percentage), non_partitionable_config


def _burst_ratio_from_mapping(config):
    burst_task_ratio = config.get("BurstTaskRatio", 0)
    if (
        isinstance(burst_task_ratio, bool)
        or not isinstance(burst_task_ratio, (int, float))
        or not 0 <= burst_task_ratio <= 100
    ):
        raise ValueError("BurstTaskRatio must be between 0 and 100")
    return float(burst_task_ratio)


def load_dag_experiment_config(dag_config_path):
    """Load the complete, explicit experiment configuration."""
    config = _load_dag_config_mapping(dag_config_path)
    timing_config = timing_config_from_mapping(config)
    non_partitionable_percentage, non_partitionable_config = (
        _non_partitionable_config_from_mapping(config)
    )
    burst_task_ratio = _burst_ratio_from_mapping(config)
    return (
        config["dag_list"],
        timing_config,
        non_partitionable_percentage,
        non_partitionable_config,
        burst_task_ratio,
    )


def load_dag_config(dag_config_path):
    """
    Load a dag config from a JSON file.
    Task Configuration:
    {
        "dag_list": List<List<TaskConfigObject>>,
        "RunningTimeFactor": float,
        "NonPartitionablePercentage": int (optional),
        "NonPartitionableConfig": dict (optional)
    }

    TaskConfigObject Attributes:
    
    
    HandlerId: the handler id of tasks
    RunningTime: the running time of tasks (ms)
    Dependencies: the dependencies of tasks
    Priority: the priority of tasks
    RunArgs: SIMO run arguments
    WorstRunningTime: Wrost running time for this task (ms)

    """
    # Legacy loader retained for old scripts. New experiment runners must use
    # load_dag_experiment_config so deadline and arrival scaling stay separate.
    try:
        config = _load_dag_config_mapping(dag_config_path)
        timing_config = timing_config_from_mapping(config)
        non_partitionable_percentage, non_partitionable_config = (
            _non_partitionable_config_from_mapping(config)
        )
        burst_task_ratio = _burst_ratio_from_mapping(config)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}")
        return

    if timing_config.deadline_factor != timing_config.arrival_scale:
        print(
            "Error: legacy load_dag_config cannot represent distinct "
            "DeadlineFactor and ArrivalScale"
        )
        return

    return (
        config["dag_list"],
        timing_config.deadline_factor,
        non_partitionable_percentage,
        non_partitionable_config,
        burst_task_ratio,
    )

def generate_tasks(task_config):
    """
    Generate tasks queue from the task config.
    Task Attributes:

    TaskId: task id
    HandlerId: handler id
    ReleaseTime: The relative release time of task, depends on Period, ReleaseTimeDelay
    Deadline: The relative deadline of task, depends on Deadline, ReleaseTime and ReleaseTimeDelay
    Priority: task priority
    Dependencies: task dependencies, contains the handler id of tasks
    """
    tasks = []
    for config in task_config:
        gap = 1 / config["Period"]
        for each_period in range(config["RunningTime"]):
            start_time = config["ReleaseTimeDelay"] + each_period
            for i in range(config["Period"]):
                task = {
                    "TaskId": f"Period[{each_period}]_#{i}_Id[{config['HandlerId']}]_[{config['ReleaseTimeDelay']}]_{generate(size=7)}",
                    "HandlerId": config["HandlerId"],
                    "ReleaseTime": start_time + i * gap,
                    "Deadline": start_time + i * gap + config["Deadline"], # deadline won't extend for ReleaseTimeDelay
                    "Priority": config["Priority"],
                    "Dependencies": config["Dependencies"]
                }
                tasks.append(task)
    return tasks

def _worst_running_time_ms(task_config):
    try:
        worst_running_time = task_config["WorstRunningTime"]
    except (KeyError, TypeError) as exc:
        raise ValueError("every DAG task must define WorstRunningTime") from exc
    return _positive_number(worst_running_time, "WorstRunningTime")


def _stage_duration_ms(stage_config, parallel_stage_policy):
    if isinstance(stage_config, list):
        if not stage_config:
            raise ValueError("parallel DAG stages cannot be empty")
        durations = [_worst_running_time_ms(task) for task in stage_config]
        return max(durations) if parallel_stage_policy == "max" else sum(durations)
    return _worst_running_time_ms(stage_config)


def _resolve_generation_timing(
    *,
    time_factor,
    deadline_factor,
    arrival_scale,
    dag_repeated_times,
    parallel_stage_policy,
):
    if time_factor is not None:
        if deadline_factor is not None or arrival_scale is not None:
            raise ValueError(
                "legacy time_factor cannot be combined with deadline_factor or "
                "arrival_scale"
            )
        legacy_factor = _positive_number(time_factor, "time_factor")
        deadline_factor = legacy_factor
        arrival_scale = legacy_factor
    else:
        deadline_factor = _positive_number(
            1.0 if deadline_factor is None else deadline_factor,
            "deadline_factor",
        )
        arrival_scale = _positive_number(
            1.0 if arrival_scale is None else arrival_scale,
            "arrival_scale",
        )

    timing_config = DagTimingConfig(
        deadline_factor=deadline_factor,
        arrival_scale=arrival_scale,
        dag_repeated_times=dag_repeated_times,
        parallel_stage_policy=parallel_stage_policy,
    )
    # Reuse mapping validation for integer repetition count and stage policy.
    return timing_config_from_mapping(
        {
            "DeadlineFactor": timing_config.deadline_factor,
            "ArrivalScale": timing_config.arrival_scale,
            "DagRepeatedTimes": timing_config.dag_repeated_times,
            "ParallelStagePolicy": timing_config.parallel_stage_policy,
        }
    )


def generate_tasks_from_dag(
    dag_config,
    time_factor=None,
    non_partitionable_percentage=0.0,
    non_partitionable_config=None,
    *,
    deadline_factor=None,
    arrival_scale=None,
    dag_repeated_times=10,
    parallel_stage_policy="max",
    seed=0,
):
    """
    Generate tasks queue from the task config.
    Task Attributes:

    TaskId: task id
    DagPeriod: the period time of DAG
    HandlerId: handler id
    ReleaseTime: The relative release time of task, depends on ReleaseTimeDelay and DagPeriod
    Deadline: The relative deadline of task, depends on Deadline, ReleaseTime and ReleaseTimeDelay
    Priority: task priority
    Dependencies: task dependencies, contains the handler id of tasks
    RunArgs: SIMO run arguments
    IsNonPartitionable: flag indicating if task is non-partitionable
    """
    timing_config = _resolve_generation_timing(
        time_factor=time_factor,
        deadline_factor=deadline_factor,
        arrival_scale=arrival_scale,
        dag_repeated_times=dag_repeated_times,
        parallel_stage_policy=parallel_stage_policy,
    )
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if (
        isinstance(non_partitionable_percentage, bool)
        or not isinstance(non_partitionable_percentage, (int, float))
        or not 0 <= non_partitionable_percentage <= 100
    ):
        raise ValueError("non_partitionable_percentage must be between 0 and 100")
    tasks = []
    start_time_ms = 0.0

    def generate_task_obj(
        config,
        start_time,
        period,
        dag_idx,
        stage_idx,
        branch_idx,
        is_non_partitionable=False,
    ):
        worst_running_time_ms = _worst_running_time_ms(config)
        branch_label = "single" if branch_idx is None else str(branch_idx)
        task_position = (
            f"dag={dag_idx}/period={period}/stage={stage_idx}/branch={branch_label}"
        )
        merge_key = f"dag={dag_idx}/period={period}/stage={stage_idx}"
        task_id = (
            f"{config['TaskName']}_[{period}]_D{dag_idx}_S{stage_idx}_B"
            f"{branch_label}"
        )
        task = {
            "TaskId": task_id,
            "TaskPosition": task_position,
            "MergeKey": merge_key,
            "ConstituentTaskIds": [task_id],
            "DagPeriod": period,
            "HandlerId": config["HandlerId"], # always 5
            "ReleaseTime": start_time / 1000,
            "Deadline": (
                start_time
                + worst_running_time_ms * timing_config.deadline_factor
            )
            / 1000,
            "Priority": config["Priority"],
            "Dependencies": config["Dependencies"],
            "RunArgs": str(config["RunArgs"]),
            "IsNonPartitionable": is_non_partitionable
        }
        return task

    # Calculate total number of tasks to determine how many should be non-partitionable
    total_tasks = 0
    for dag in dag_config:
        for _ in range(timing_config.dag_repeated_times):
            for config in dag:
                if isinstance(config, list):
                    total_tasks += len(config)
                else:
                    total_tasks += 1
    
    non_partitionable_count = int(total_tasks * non_partitionable_percentage / 100)
    
    # Generate all task positions and randomly select non-partitionable ones
    all_task_positions = []
    for dag_idx, dag in enumerate(dag_config):
        for period in range(timing_config.dag_repeated_times):
            for config_idx, config in enumerate(dag):
                if isinstance(config, list):
                    for sub_idx, _ in enumerate(config):
                        all_task_positions.append(
                            (dag_idx, period, config_idx, sub_idx)
                        )
                else:
                    all_task_positions.append((dag_idx, period, config_idx, None))
    
    # Rank every structural position with a stable hash. Taking a prefix makes
    # 0/50/100% atomic sets nested and independent of Python's RNG version.
    def position_rank(position):
        encoded = f"{seed}|{position!r}".encode("utf-8")
        return hashlib.sha256(encoded).digest()

    ranked_positions = sorted(all_task_positions, key=position_rank)
    non_partitionable_positions = set(
        ranked_positions[:non_partitionable_count]
    )
    
    # Generate tasks with non-partitionable selection
    for dag_idx, dag in enumerate(dag_config):
        for period in range(timing_config.dag_repeated_times):
            for config_idx, config in enumerate(dag):
                stage_start_ms = start_time_ms
                if isinstance(config, list):
                    for sub_idx, subconfig in enumerate(config):
                        is_non_partitionable = (
                            dag_idx,
                            period,
                            config_idx,
                            sub_idx,
                        ) in non_partitionable_positions
                        task = generate_task_obj(
                            subconfig,
                            stage_start_ms,
                            period,
                            dag_idx,
                            config_idx,
                            sub_idx,
                            is_non_partitionable,
                        )
                        tasks.append(task)
                else:
                    is_non_partitionable = (
                        dag_idx,
                        period,
                        config_idx,
                        None,
                    ) in non_partitionable_positions
                    task = generate_task_obj(
                        config,
                        stage_start_ms,
                        period,
                        dag_idx,
                        config_idx,
                        None,
                        is_non_partitionable,
                    )
                    tasks.append(task)

                start_time_ms += (
                    _stage_duration_ms(
                        config, timing_config.parallel_stage_policy
                    )
                    * timing_config.arrival_scale
                )
    return tasks


def task_stream_sha256(tasks):
    """Hash the offered task stream before method-specific scheduling changes."""
    canonical_tasks = [
        {key: value for key, value in task.items() if key != "SignalMsg"}
        for task in tasks
    ]
    payload = json.dumps(
        canonical_tasks,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def overall_deadline_seconds(dag_config, timing_config):
    """Return the maximum absolute node deadline in the generated run."""
    timing_config = _resolve_generation_timing(
        time_factor=None,
        deadline_factor=timing_config.deadline_factor,
        arrival_scale=timing_config.arrival_scale,
        dag_repeated_times=timing_config.dag_repeated_times,
        parallel_stage_policy=timing_config.parallel_stage_policy,
    )
    start_time_ms = 0.0
    maximum_deadline_ms = 0.0

    for dag in dag_config:
        for _ in range(timing_config.dag_repeated_times):
            for stage_config in dag:
                stage_tasks = (
                    stage_config if isinstance(stage_config, list) else [stage_config]
                )
                for task_config in stage_tasks:
                    maximum_deadline_ms = max(
                        maximum_deadline_ms,
                        start_time_ms
                        + _worst_running_time_ms(task_config)
                        * timing_config.deadline_factor,
                    )
                start_time_ms += (
                    _stage_duration_ms(
                        stage_config, timing_config.parallel_stage_policy
                    )
                    * timing_config.arrival_scale
                )

    return maximum_deadline_ms / 1000.0


if __name__ == "__main__":
    (
        dag_config,
        timing_config,
        non_partitionable_percentage,
        non_partitionable_config,
        _,
    ) = load_dag_experiment_config("TaskConfigs/simo/agx_tight.json")
    tasks = generate_tasks_from_dag(
        dag_config,
        deadline_factor=timing_config.deadline_factor,
        arrival_scale=timing_config.arrival_scale,
        dag_repeated_times=timing_config.dag_repeated_times,
        parallel_stage_policy=timing_config.parallel_stage_policy,
        non_partitionable_percentage=non_partitionable_percentage,
        non_partitionable_config=non_partitionable_config,
        seed=timing_config.task_seed,
    )
    print(f"Generated {len(tasks)} DAG tasks")
