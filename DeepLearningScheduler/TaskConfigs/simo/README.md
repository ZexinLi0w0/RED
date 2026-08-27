### SIMO 任务配置说明

**SIMO（Simple Input Multi Output）** 指对模型进行结构化优化后，通过一次输入按需“局部激活”不同子路径（子模块）来完成不同任务的运行模式。调度器通过传入激活参数 RunArgs 来选择性启用模型的某些分支，从而以更低的开销完成特定任务。

- **HandlerId=5**: 表示使用 SIMO 模型的处理器。在任务图中凡是 `HandlerId` 为 5 的条目，均调用 SIMO 模型并依据 `RunArgs` 激活对应子模块。
- **RunArgs**: 为激活参数。可为简洁的索引（如 `[1]`, `[2]`, `[3]`, `[4]`）。调度器会将该参数传递给 SIMO 的处理逻辑，以启用对应分支或阶段。

### 配置文件结构

常见字段如下（不同文件可能包含其子集或扩展字段）：

- **dag_list**: 任务图定义。最外层数组包含一批或多批子图（scene/stream）。
  - 每个子图本身是一个数组，内部按照从前到后的阶段组织；
  - 数组元素可以是单个任务对象，或一个由多个任务对象组成的数组（表示可并行的同层任务）。
- **TaskName**: 任务名称，便于日志与分析。
- **HandlerId**: 处理器标识。`5` 表示 SIMO 模型。
- **RunArgs**: SIMO 激活参数。决定启用的子模块/阶段。
- **Dependencies**: 依赖的上游任务 ID 列表。ID 由调度器按拓扑顺序分配（从 1 开始递增），用于表示先后/并行关系。
- **Priority**: 调度优先级（数值越大越重要，实际含义依据调度策略）。
- **RunningTime**: 该任务的目标/预算运行时长（毫秒级，可选，用于节奏控制或统计）。
- **WorstRunningTime**: 最坏情况下的运行时间估计（毫秒），用于超时和鲁棒性控制。
- 可选全局字段：
  - **RunningTimeFactor**: 全局时间缩放因子，用于模拟不同平台/工况下的执行时延。
  - **NonPartitionablePercentage**: 指定不可切分比例（%），用于评估任务在细粒度切分下的不可并行部分。
  - **DropThreshold**（任务级可选属性）: 面向突发（burst）场景的任务丢弃阈值；当前实现仅使用该字段。

### Burst 工作负载配置

Burst 实验通过单独的 JSON 文件定义绝对释放窗口。所有调度方法使用同一份
Burst 工作负载；只有 `feedback-fine-grained`（RED）启用过载检测和主动丢弃。

- **burst_regime**: `transient` 或 `sustained`。
- **burst_start_seconds**: Burst 相对于实验起点的开始时间。
- **transient_duration_seconds**: 仅用于 transient，定义有限 Burst 窗口长度。
- **release_horizon_seconds**: 基础工作负载的释放时间范围上界；sustained Burst
  从开始时间持续到该上界。
- **BurstTaskRatio**（任务配置字段）: `100` 表示为窗口内每个基础 DAG release
  增加一个完整 DAG；`50` 表示对窗口内按时间均匀分布的一半 releases 各增加
  一个完整 DAG。克隆 DAG 保留原始 release time、deadline 和 priority，但使用
  独立的 DAG-period identity。

### 示例 1：索引型 RunArgs

```json
{
  "dag_list": [
    [
      {"TaskName": "S1_Stage1_LaneDetection", "HandlerId": 5, "RunArgs": [1], "Dependencies": [], "Priority": 1, "WorstRunningTime": 60},
      {"TaskName": "S1_Stage2_Segmentation", "HandlerId": 5, "RunArgs": [3], "Dependencies": [1], "Priority": 1, "WorstRunningTime": 45},
      {"TaskName": "S1_Stage3_Control_Autopilot", "HandlerId": 5, "RunArgs": [2], "Dependencies": [3], "Priority": 1, "WorstRunningTime": 45}
    ]
  ]
}
```

说明：三个阶段串行执行，均由 SIMO 模型完成，但通过不同的 `RunArgs` 分别激活车道线、分割与控制三个子路径。

### 示例 2：键值型 RunArgs 与并行阶段

```json
{
  "dag_list": [
    [
      {"TaskName": "Preprocess", "HandlerId": 5, "Priority": 2, "Dependencies": [], "RunArgs": {"stage": "preprocess", "notes": "resize_normalize"}, "WorstRunningTime": 20},
      [
        {"TaskName": "Detect", "HandlerId": 5, "Priority": 3, "Dependencies": [], "RunArgs": {"stage": "detect", "model": "yolov5n"}, "WorstRunningTime": 60},
        {"TaskName": "Segment", "HandlerId": 5, "Priority": 3, "Dependencies": [], "RunArgs": {"stage": "segment", "model": "unet"}, "WorstRunningTime": 55}
      ],
      {"TaskName": "Postprocess", "HandlerId": 5, "Priority": 2, "Dependencies": [], "RunArgs": {"stage": "postprocess", "notes": "nms_merge"}, "WorstRunningTime": 25}
    ]
  ],
  "RunningTimeFactor": 1.0,
  "NonPartitionablePercentage": 15
}
```

说明：`Detect` 与 `Segment` 处于同一层数组，表示可并行执行。各任务通过键值型 `RunArgs` 指定更可读的阶段/模型参数。

### 使用建议

- 在同一条流水线中，不同任务通过不同 `RunArgs` 选择性激活 SIMO 的子模块，避免重复加载与冗余计算。
- 串行/并行关系以 `dag_list` 的层次与 `Dependencies` 描述；并行任务置于同一数组层级。
- 若迁移到不同硬件平台，可通过 `RunningTimeFactor` 进行统一的时间尺度调整。

