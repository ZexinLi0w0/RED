# Non-Partitionable Tasks Feature Planning Document

## Overview

This document outlines the plan to add support for Non-Partitionable Tasks to the DeepLearningScheduler system. Non-Partitionable Tasks are tasks that cannot be divided into several sub-tasks even when they have DAG configurations. The goal is to support random non-partitionable tasks (configurable percentage, e.g., 15%) in the overall task mix.

## Current System Analysis

### 1. Task Types Currently Supported

The system currently supports two main task types:

#### A. Regular Tasks (task_config format)
- **File**: `TaskConfigs/*.json` (e.g., `concurrency.json`, `dynamic-addtask.json`)
- **Structure**: Uses `task_list` array with individual task configurations
- **Attributes**: HandlerId, Period, Deadline, RunningTime, Priority, Dependencies, ReleaseTimeDelay
- **Generation**: Uses `generate_tasks()` function in `task_generator.py`

#### B. DAG Tasks (dag_config format)  
- **File**: `TaskConfigs/simo/*.json` (e.g., `agx_loose.json`, `nano_tight.json`)
- **Structure**: Uses `dag_list` array with DAG configurations
- **Attributes**: TaskName, HandlerId, RunningTime, Dependencies, Priority, RunArgs, WorstRunningTime
- **Generation**: Uses `generate_tasks_from_dag()` function in `task_generator.py`

### 2. Current Task Processing Flow

```
main.py → parseArguments() → load_dag_config() → generate_tasks_from_dag() → TaskSchedule → controller_signaling_SIMO
```

### 3. Key Components Analysis

#### A. Task Generator (`task_generator.py`)
- **Current Logic**: 
  - `load_dag_config()`: Loads DAG configuration with `dag_list` and `RunningTimeFactor`
  - `generate_tasks_from_dag()`: Creates individual tasks from DAG structure
  - Each DAG task gets `DagPeriod`, `RunArgs`, and other DAG-specific attributes
  - Tasks are generated with sequential timing based on DAG dependencies

#### B. Task Scheduler (`task_scheduler.py`)
- **Current Logic**:
  - `generate_task_list()`: Creates signal messages for each task
  - `fine_grained_adjust()`: Merges tasks with similar release times (only for DAG tasks)
  - `feedback_adjust()`: Adjusts release times based on execution feedback
  - Dependency management through `task_dependency` dictionary

#### C. Controller Signaling (`controller_signaling.py`)
- **Current Logic**:
  - `controller_signaling_SIMO()`: Handles SIMO-specific task processing
  - Processes task delivery signals with SIMO arguments
  - Manages task dependencies and skipped tasks

#### D. Handler Signaling (`handler_signaling.py`)
- **Current Logic**:
  - `handle_signaling_SIMO()`: Executes tasks with decoder lists
  - Processes SIMO-specific arguments and DAG periods

## Required Changes for Non-Partitionable Tasks Support

### Phase 1: Configuration Schema Extension

#### Step 1.1: Extend DAG Configuration Schema
**Current Implementation**: DAG config only supports partitionable tasks
**Required Changes**:
- Add `NonPartitionablePercentage` field to DAG configuration
- Add `IsNonPartitionable` flag to individual task configurations
- Add `NonPartitionableConfig` section for non-partitionable task parameters

**Files to Modify**:
- `task_generator.py`: `load_dag_config()` function
- `TaskConfigs/simo/*.json`: Configuration files

**Example Configuration**:
```json
{
  "RunningTimeFactor": 1.5,
  "NonPartitionablePercentage": 15,
  "NonPartitionableConfig": {
    "HandlerId": 5,
    "WorstRunningTime": 150,
    "Priority": 2
  },
  "dag_list": [...]
}
```

#### Step 1.2: Update Task Validation
**Current Implementation**: `validate_task_config()` only validates regular task attributes
**Required Changes**:
- Add validation for non-partitionable task attributes
- Ensure non-partitionable tasks have required fields
- Validate percentage configuration

**Files to Modify**:
- `task_generator.py`: `validate_task_config()` function

### Phase 2: Task Generation Logic

#### Step 2.1: Modify DAG Task Generation
**Current Implementation**: `generate_tasks_from_dag()` creates only partitionable tasks
**Required Changes**:
- Add logic to randomly select tasks as non-partitionable based on percentage
- Generate non-partitionable tasks with different attributes
- Ensure non-partitionable tasks maintain DAG dependencies

**Files to Modify**:
- `task_generator.py`: `generate_tasks_from_dag()` function

**Implementation Details**:
```python
def generate_tasks_from_dag(dag_config, time_factor=1, non_partitionable_percentage=0):
    # Existing logic for partitionable tasks
    # New logic:
    # 1. Calculate number of non-partitionable tasks
    # 2. Randomly select tasks to be non-partitionable
    # 3. Generate non-partitionable task objects with different attributes
    # 4. Maintain dependency relationships
```

#### Step 2.2: Add Non-Partitionable Task Attributes
**Current Implementation**: Tasks have `DagPeriod`, `RunArgs`, etc.
**Required Changes**:
- Add `IsNonPartitionable` flag to task objects
- Add `NonPartitionableType` identifier
- Modify task ID generation for non-partitionable tasks

**Files to Modify**:
- `task_generator.py`: `generate_task_obj()` function

### Phase 3: Task Scheduling Logic

#### Step 3.1: Update Task Scheduler
**Current Implementation**: `TaskSchedule` treats all tasks equally
**Required Changes**:
- Add non-partitionable task handling in `generate_task_list()`
- Modify `fine_grained_adjust()` to exclude non-partitionable tasks from merging
- Update task statistics initialization

**Files to Modify**:
- `task_scheduler.py`: `TaskSchedule` class

**Implementation Details**:
```python
def generate_task_list(self):
    # Existing logic
    # New logic:
    # 1. Check if task is non-partitionable
    # 2. Generate different signal messages for non-partitionable tasks
    # 3. Skip fine-grained adjustment for non-partitionable tasks
```

#### Step 3.2: Modify Fine-Grained Adjustment
**Current Implementation**: `fine_grained_adjust()` merges all tasks with similar timing
**Required Changes**:
- Add logic to identify and exclude non-partitionable tasks from merging
- Maintain non-partitionable task integrity

**Files to Modify**:
- `task_scheduler.py`: `fine_grained_adjust()` method

### Phase 4: Controller and Handler Signaling

#### Step 4.1: Update Controller Signaling
**Current Implementation**: `controller_signaling_SIMO()` processes all tasks uniformly
**Required Changes**:
- Add non-partitionable task detection in signal processing
- Handle non-partitionable task delivery signals differently
- Update dependency management for non-partitionable tasks

**Files to Modify**:
- `controller_signaling.py`: `controller_signaling_SIMO()` function

#### Step 4.2: Update Handler Signaling
**Current Implementation**: `handle_signaling_SIMO()` executes tasks with decoder lists
**Required Changes**:
- Add non-partitionable task execution logic
- Handle different signal arguments for non-partitionable tasks
- Update task completion reporting

**Files to Modify**:
- `handler_signaling.py`: `handle_signaling_SIMO()` function

### Phase 5: Statistics and Visualization

#### Step 5.1: Update Task Statistics
**Current Implementation**: `init_task_statistics()` records standard task attributes
**Required Changes**:
- Add non-partitionable task tracking in statistics
- Include non-partitionable task metrics in analysis

**Files to Modify**:
- `task_scheduler.py`: `init_task_statistics()` method
- `visual_scripts/visual_task.py`: Statistics computation functions

#### Step 5.2: Update Visualization
**Current Implementation**: Visualization treats all tasks equally
**Required Changes**:
- Add visual distinction for non-partitionable tasks
- Include non-partitionable task metrics in plots
- Update scatter plots and box plots

**Files to Modify**:
- `visual_scripts/visual_task.py`: All visualization functions

### Phase 6: Configuration and Testing

#### Step 6.1: Create Test Configurations
**Required Changes**:
- Create test DAG configurations with non-partitionable tasks
- Add validation tests for non-partitionable task generation
- Create performance comparison tests

**Files to Create**:
- `TaskConfigs/simo/test_non_partitionable.json`
- Test scripts for validation

#### Step 6.2: Update Main Entry Point
**Current Implementation**: `main.py` loads DAG config and generates tasks
**Required Changes**:
- Add non-partitionable percentage parameter handling
- Update task generation calls

**Files to Modify**:
- `main.py`: `parseArguments()` and task loading logic

## Implementation Steps

### Step 1: Configuration Schema (Priority: High)
1. Update DAG configuration schema to include non-partitionable parameters
2. Add validation for new configuration fields
3. Create sample configurations for testing

### Step 2: Task Generation (Priority: High)
1. Modify `generate_tasks_from_dag()` to support non-partitionable tasks
2. Add random selection logic for non-partitionable tasks
3. Update task object generation with new attributes

### Step 3: Task Scheduling (Priority: High)
1. Update `TaskSchedule` class to handle non-partitionable tasks
2. Modify `fine_grained_adjust()` to exclude non-partitionable tasks
3. Update task statistics initialization

### Step 4: Signaling System (Priority: Medium)
1. Update controller signaling for non-partitionable tasks
2. Modify handler signaling for non-partitionable task execution
3. Test signal flow with non-partitionable tasks

### Step 5: Statistics and Visualization (Priority: Medium)
1. Update task statistics to include non-partitionable task data
2. Modify visualization functions to distinguish task types
3. Add non-partitionable task metrics to analysis

### Step 6: Testing and Validation (Priority: Medium)
1. Create comprehensive test cases
2. Validate non-partitionable task behavior
3. Performance testing with mixed task types

## Risk Assessment and Mitigation

### Risks:
1. **Breaking Changes**: Modifying existing task generation logic
2. **Performance Impact**: Additional logic for non-partitionable task handling
3. **Dependency Management**: Ensuring non-partitionable tasks maintain DAG dependencies
4. **Visualization Complexity**: Adding new task types to existing plots

### Mitigation Strategies:
1. **Backward Compatibility**: Maintain existing functionality while adding new features
2. **Incremental Implementation**: Implement changes in phases with testing at each step
3. **Comprehensive Testing**: Create extensive test cases for all scenarios
4. **Documentation**: Update all relevant documentation and comments

## Success Criteria

1. **Functional Requirements**:
   - System can generate mixed partitionable and non-partitionable tasks
   - Non-partitionable tasks maintain their integrity (no merging)
   - DAG dependencies are preserved for all task types
   - Statistics and visualization distinguish between task types

2. **Performance Requirements**:
   - No significant performance degradation with non-partitionable tasks
   - Configurable percentage of non-partitionable tasks (e.g., 15%)
   - Proper handling of edge cases (0%, 100% non-partitionable)

3. **Quality Requirements**:
   - All existing functionality remains intact
   - Comprehensive test coverage for new features
   - Clear documentation and examples


## Conclusion

This plan provides a comprehensive approach to adding Non-Partitionable Tasks support to the DeepLearningScheduler system. The implementation will be done incrementally to minimize risk and ensure backward compatibility. Each phase includes specific deliverables and testing requirements to ensure quality and functionality. 


## Usage
### 1. Basic Usage with Non-Partitionable Tasks
```bash
# cd /experiment/zexin/ATC23/DeepLearningScheduler
# agx_loose_non_partitionable.json 里的 NonPartitionablePercentage 来控制不可划分任务的比例.
# 使用 cat /sys/devices/platform/gpu.0/load 查看 gpu 占用率(0-1000)
# Nano Tight Non-Partitionable Task Config - Baseline Approach(EDF)
python main.py --config handler-config.json --task TaskConfigs/simo/agx_loose_non_partitionable.json --approach baseline

# Feedback-fine-grained Approach(RED)
python main.py --config handler-config.json --task TaskConfigs/simo/agx_loose_non_partitionable.json --approach feedback-fine-grained


# Nano config
python main.py --config handler-config.json --task TaskConfigs/simo/nano_loose_non_partitionable.json --approach baseline
python main.py --config handler-config.json --task TaskConfigs/simo/nano_loose_non_partitionable.json --approach feedback-fine-grained
```

