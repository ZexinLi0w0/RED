# 深度学习任务调度系统

## 项目概述与实现方法

这是一个用于管理和调度深度学习任务的分布式调度系统。该系统采用多进程架构，通过信号机制实现控制器与处理器之间的通信，支持多种调度策略和任务优化方法。

### 核心架构

系统采用**主从架构**：
- **主进程（Controller）**：负责任务调度、状态管理和信号分发
- **子进程（Handlers）**：执行具体的深度学习任务，每个Handler运行在独立的进程中

### 实现原理

#### 1. 进程间通信机制
- 使用Python的`multiprocessing.Queue`实现进程间通信
- 通过自定义的信号协议（`SignalCommand`）进行任务控制
- 支持异步操作，使用`asyncio`处理并发任务

#### 2. 状态机管理
每个Handler遵循有限状态机（FSM）模式：
- **Entry**: 初始状态
- **Load**: 加载数据和模型
- **Ready**: 准备就绪，等待任务
- **Running**: 执行任务中
- **Error**: 错误状态
- **Exit**: 退出状态

#### 3. 调度策略
支持多种调度算法：
- **EDF (Earliest Deadline First)**: 最早截止时间优先
- **Priority**: 优先级调度
- **FCFS (First Come First Serve)**: 先到先服务
- **RR (Round Robin)**: 轮转调度

#### 4. 任务优化方法
提供四种任务调整策略：
- **Baseline**: 基础调度，不做任何调整
- **Feedback**: 根据任务执行反馈调整下次释放时间
- **Fine-grained**: 在任务生成时重构DAG结构
- **Feedback-fine-grained**: 结合反馈和细粒度调整

## 核心文件详细说明

### 1. main.py - 主程序入口

#### 主要函数说明：

**`create_subprocess(control_queue, base_time, config=())`**
- **功能**: 在独立进程中创建和运行单个Handler
- **参数**: 
  - `control_queue`: 进程间通信队列
  - `base_time`: 系统启动基准时间
  - `config`: Handler配置元组 (handler_id, handler_name, handler_description, runargs)
- **工作流程**:
  1. 动态导入对应的Handler模块
  2. 创建Handler实例
  3. 启动异步事件循环处理信号
  4. 调用`handle_signaling_SIMO`处理信号响应

**`run_handlers(handlers, tasks_list, control_queue, logger, approach_module='baseline', task_filename="task_config")`**
- **功能**: 并发运行多个Handler进程
- **参数**:
  - `handlers`: Handler配置列表
  - `tasks_list`: 任务列表
  - `control_queue`: 控制信号队列
  - `logger`: 日志记录器
  - `approach_module`: 任务调整策略
  - `task_filename`: 任务配置文件名
- **工作流程**:
  1. 为每个Handler创建独立进程
  2. 启动所有进程
  3. 创建控制器信号处理任务
  4. 运行事件循环直到所有任务完成

**`parseArguments()`**
- **功能**: 解析命令行参数和配置文件
- **返回值**: (handlers, tasks_list, approach_module, filename)
- **工作流程**:
  1. 解析命令行参数（--config, --task, --approach）
  2. 加载和验证Handler配置文件
  3. 加载DAG任务配置
  4. 生成任务列表
  5. 提取任务配置文件名

### 2. AbstractHandler.py - 抽象处理器基类

#### 类说明：

**`HandlerStatus`枚举**
- 定义Handler的6种状态：Entry, Load, Ready, Running, Error, Exit

**`AbstractHandler`抽象基类**
- **`__init__(task_id, task_name, task_description)`**: 初始化Handler基本信息
- **`run()`**: 抽象方法，执行具体任务
- **`stop()`**: 抽象方法，停止任务执行
- **`load_data()`**: 抽象方法，加载模型和数据
- **`ready()`**: 抽象方法，准备就绪
- **`exception()`**: 抽象方法，异常处理
- **`exit()`**: 抽象方法，退出清理

### 3. control_signal.py - 信号控制模块

#### 主要函数说明：

**`SignalCommand`枚举**
- 定义信号类型：PING, LOADDATA, READY, RUN, DELIVERY, STOP, EXIT

**`generate_signal(taskid, signal, *args)`**
- **功能**: 生成信号字符串
- **参数**: 
  - `taskid`: 目标Handler ID
  - `signal`: 信号命令
  - `*args`: 附加参数
- **返回**: 格式化的信号字符串

**`parse_signal(signal_str)`**
- **功能**: 解析信号字符串
- **参数**: `signal_str`: 信号字符串
- **返回**: (taskid, signal, *args) 元组

**`convert_args_to_dict(args_data)`**
- **功能**: 将参数列表转换为字典
- **参数**: `args_data`: 参数列表或字符串
- **返回**: 参数字典

### 4. handler_signaling.py - 处理器信号处理

#### 主要函数说明：

**`handle_signaling(control_queue, base_time, config=(), logger=logging, instance=None)`**
- **功能**: 普通Handler的信号响应处理
- **工作流程**:
  1. 进入无限循环监听信号
  2. 根据信号类型执行相应操作：
     - PING: 返回心跳状态
     - LOADDATA: 加载数据并更新状态
     - READY: 设置就绪状态
     - RUN: 执行任务并返回结果

**`handle_signaling_SIMO(control_queue, base_time, config=(), logger=logging, instance=None)`**
- **功能**: SIMO Handler的信号响应处理（支持多任务）
- **特殊功能**:
  - 支持`decoder_list`参数指定执行的任务类型
  - 处理SIMO特定的参数（simo_args, dag_period）
  - 支持跳过模式（skipmode）

### 5. controller_signaling.py - 控制器信号处理

#### 主要函数说明：

**`send_heart_ping(control_queue, handlers, logger=logging, base_time=0)`**
- **功能**: 发送心跳信号到所有Handler
- **工作流程**:
  1. 每60ms向所有Handler发送PING信号
  2. 监控Handler状态变化

**`controller_signaling(control_queue, handlers, tasks_list, logger=logging, base_time=0, approach_module='baseline')`**
- **功能**: 普通控制器的信号处理逻辑
- **工作流程**:
  1. 初始化Handler状态和任务调度器
  2. 发送LOADDATA信号启动Handler
  3. 等待所有Handler就绪后生成任务列表
  4. 分发任务并处理完成反馈

**`controller_signaling_SIMO(control_queue, handlers, tasks_list, approach_module='baseline', logger=logging, base_time=0, task_filename='task-config')`**
- **功能**: SIMO控制器的信号处理逻辑
- **特殊功能**:
  - 支持SIMO特定的任务反馈调整
  - 处理多任务依赖关系
  - 支持跳过依赖任务的处理

### 6. task_scheduler.py - 任务调度器

#### 类说明：

**`TaskSchedule`类**

**`__init__(tasks, handler_status={}, control_queue=[], scheduler='priority', custom_scheduler=None, logger=logging, approach_module='baseline', task_filename='task_config')`**
- **功能**: 初始化任务调度器
- **参数**:
  - `tasks`: 任务列表
  - `handler_status`: Handler状态字典
  - `control_queue`: 控制队列
  - `scheduler`: 调度算法名称
  - `approach_module`: 任务调整策略

**`generate_task_list()`**
- **功能**: 生成任务列表并应用调度算法
- **工作流程**:
  1. 为每个任务生成信号消息
  2. 根据调整策略进行任务优化
  3. 应用调度算法排序任务
  4. 初始化任务统计信息

**`distribute_tasks()`**
- **功能**: 分发任务到Handler
- **工作流程**:
  1. 检查任务释放条件
  2. 检查Handler就绪状态
  3. 检查任务依赖关系
  4. 发送任务信号或重新排队

**`release_met(handlers, task=None, now_time=time.time())`**
- **功能**: 检查任务释放条件是否满足
- **条件**: 当前时间 >= 释放时间 && Handler就绪 && 依赖满足

**`dependencies_met(task)`**
- **功能**: 检查任务依赖是否满足
- **逻辑**: 验证同一DAG周期内的所有依赖任务已完成

**`feedback_adjust(end_time)`**
- **功能**: 根据任务执行反馈调整下次任务释放时间
- **策略**: 如果当前任务提前完成，将下次任务释放时间提前

**`fine_grained_adjust(merge_tick=0.02, merge_handler=[5])`**
- **功能**: 细粒度调整，合并相近时间的任务
- **策略**: 将时间间隔小于merge_tick的同类型任务合并

**调度算法方法**:
- **`edf()`**: 最早截止时间优先排序
- **`priority()`**: 按优先级排序
- **`fcfs()`**: 按释放时间排序（先到先服务）
- **`fcls()`**: 按释放时间逆序排序
- **`rr()`**: 轮转调度（待实现）

### 7. task_generator.py - 任务生成器

#### 主要函数说明：

**`load_task_config(task_config_path)`**
- **功能**: 加载普通任务配置文件
- **返回**: 任务配置列表
- **验证**: 检查必需属性和数据类型

**`load_dag_config(dag_config_path)`**
- **功能**: 加载DAG任务配置文件
- **返回**: (dag_config, running_time_factor)
- **支持**: 时间因子调整

**`generate_tasks(task_config)`**
- **功能**: 从普通配置生成任务列表
- **逻辑**: 根据周期、运行时间等参数生成具体任务

**`generate_tasks_from_dag(dag_config, time_factor=1)`**
- **功能**: 从DAG配置生成任务列表
- **特点**: 支持DAG依赖关系和SIMO参数

### 8. validate_handlers.py - 处理器验证

#### 主要函数说明：

**`validate_handlers(handlers)`**
- **功能**: 验证Handler配置的有效性
- **检查项**:
  - 必需属性完整性
  - Handler名称唯一性
  - Handler ID唯一性

### 9. logging_config.py - 日志配置

#### 主要函数说明：

**`logging_basic_setting(name='main')`**
- **功能**: 设置彩色日志输出
- **特性**:
  - 彩色控制台输出
  - 分级文件日志
  - 统一的日志格式

## 工作流程详解

### 1. 系统启动流程
```
main.py → parseArguments() → 加载配置 → 验证配置 → 创建进程
```

### 2. Handler启动流程
```
create_subprocess() → 动态导入Handler → 创建实例 → 启动信号处理循环
```

### 3. 任务调度流程
```
controller_signaling() → 等待Handler就绪 → generate_task_list() → distribute_tasks()
```

### 4. 任务执行流程
```
发送RUN信号 → Handler执行任务 → 返回DELIVERY信号 → 更新统计信息
```

### 5. 结果收集流程
```
after_finsihed_task_distribution() → 保存统计数据 → 生成性能报告
```

## 特色功能详解

### 1. 多进程并发处理
- 每个Handler运行在独立进程中
- 使用Queue进行进程间通信
- 支持CPU密集型任务的并行执行

### 2. 实时任务调度
- 支持动态任务调整
- 基于反馈的任务优化
- 实时监控任务执行状态

### 3. 依赖关系管理
- 支持DAG任务依赖
- 自动处理依赖任务跳过
- 跨周期依赖管理

### 4. 性能监控与分析
- 详细的执行时间统计
- 截止时间违反率分析
- 可视化性能报告

### 5. 灵活的调度策略
- 多种经典调度算法
- 支持自定义调度器
- 可配置的任务优化策略

### 6. SIMO多任务支持
- 专门的多任务学习模型调度
- 支持任务类型选择
- 多任务依赖处理

## 使用示例

### 基础使用
```bash
python main.py -c handler-config.json -t task-config.json -a baseline
```

### SIMO实验
```bash
# 基线实验
python main.py -c simo-handler_config.json -t TaskConfigs/simo/agx_loose.json -a baseline

# 反馈优化
python main.py -c simo-handler_config.json -t TaskConfigs/simo/agx_loose.json -a feedback

# 细粒度调整
python main.py -c simo-handler_config.json -t TaskConfigs/simo/agx_loose.json -a fine-grained

# 组合优化
python main.py -c simo-handler_config.json -t TaskConfigs/simo/agx_loose.json -a feedback-fine-grained
```

## 配置说明

### Handler配置文件格式
```json
{
    "handler_list": [
        {
            "id": 1,
            "name": "handler1",
            "description": "自动驾驶控制处理器"
        }
    ]
}
```

### 任务配置文件格式
```json
{
    "task_list": [
        {
            "HandlerId": 1,
            "Period": 30,
            "Deadline": 0.01,
            "RunningTime": 1,
            "Dependencies": [],
            "Priority": 1
        }
    ]
}
```

### DAG配置文件格式
```json
{
    "dag_list": [
        [
            {
                "TaskName": "Stage1_LaneDetection",
                "HandlerId": 5,
                "WorstRunningTime": 110,
                "Dependencies": [],
                "Priority": 1,
                "RunArgs": [1]
            }
        ]
    ],
    "RunningTimeFactor": 1
}