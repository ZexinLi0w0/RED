# Burst Task Management Implementation

## Overview

This implementation adds burst task support to the existing Deep Learning Scheduler system. The burst task management mechanism provides proactive task dropping capabilities to handle dynamic and unpredictable workload patterns in real-time deployment scenarios.

## Key Features

### 1. System Health Monitoring
- **GPU Utilization Monitoring**: Continuous monitoring of GPU usage percentage
- **Queue Length Tracking**: Real-time tracking of task queue length
- **Deadline Slack Calculation**: Dynamic calculation of task deadline slack time

### 2. Proactive Task Dropping
- **Overload Detection**: Automatic detection of system overload conditions
- **Criticality Scoring**: Enhanced criticality score calculation with configurable weights
- **Intelligent Task Selection**: Drop lower criticality tasks while preserving high-priority tasks

### 3. Enhanced Task Data Structure
- **BurstPriority**: Separate priority for burst management scenarios
- **CriticalityWeight**: Configurable weight for criticality score calculation
- **DropThreshold**: Individual task drop threshold for fine-grained control

## Architecture

### Core Components

#### 1. SystemHealthMonitor
```python
class SystemHealthMonitor:
    - Monitors GPU utilization using nvidia-smi or tegrastats
    - Tracks queue length in real-time
    - Provides system health metrics
```

#### 2. BurstTaskManager
```python
class BurstTaskManager:
    - Implements proactive task dropping algorithm
    - Calculates enhanced criticality scores
    - Manages burst mode state transitions
```

#### 3. BurstAwareTaskScheduler
```python
class BurstAwareTaskScheduler:
    - Integrates burst management with existing schedulers
    - Provides burst-aware task scheduling
    - Maintains compatibility with existing scheduling algorithms
```

### Criticality Score Formula

The enhanced criticality score is calculated as:

```
C_i = (1 - (S_i / D_i)) * W_i * P_i
```

Where:
- `S_i = D_i - t` is the slack time
- `D_i` is the task deadline
- `t` is the elapsed time since task release
- `W_i` is the criticality weight
- `P_i` is the burst priority

### Overload Detection

System overload is detected when:
- GPU utilization > `gpu_threshold` (default: 80%)
- Queue length > `queue_threshold` (default: 10)

## Configuration

### Burst Configuration File (`burst_config.json`)
```json
{
    "burst_enabled": true,
    "gpu_threshold": 80.0,
    "queue_threshold": 10,
    "drop_percentage": 25,
    "monitoring_interval": 0.1,
    "criticality_weight": 1.0
}
```

### Task Configuration with Burst Attributes
```json
{
    "task_list": [
        {
            "HandlerId": 5,
            "ReleaseTimeDelay": 0,
            "Deadline": 0.01,
            "Period": 40,
            "RunningTime": 1,
            "Dependencies": [],
            "Priority": 1,
            "BurstPriority": 2,
            "CriticalityWeight": 1.5,
            "DropThreshold": 0.3
        }
    ]
}
```

## Usage

### 1. Basic Usage with Burst Management
```bash
# Task config
python main.py --config handler-config.json --task TaskConfigs/burst-task-config.json --approach baseline --burst-config burst_config.json

#Dag config
python main.py --config handler-config.json --task TaskConfigs/simo/burst-dag-config.json --approach baseline --burst-config burst_config.json
```

### 2. Testing Burst Functionality
```bash
python test_burst_tasks.py
```

### 3. Integration with Existing System
The burst task management is seamlessly integrated with the existing scheduling system:
- Compatible with all existing schedulers (EDF, Priority, FCFS, etc.)
- Works with all approach modules (baseline, feedback, fine-grained)
- Maintains backward compatibility

## Implementation Details

### Task Data Structure Enhancements

#### New Attributes Added:
- `BurstPriority`: Separate priority for burst scenarios
- `CriticalityWeight`: Weight factor for criticality calculation
- `DropThreshold`: Individual task drop threshold

#### Enhanced Task Generation:
```python
# In task_generator.py
task = {
    # ... existing attributes ...
    "BurstPriority": config.get("BurstPriority", config["Priority"]),
    "CriticalityWeight": config.get("CriticalityWeight", 1.0),
    "DropThreshold": config.get("DropThreshold", 0.5)
}
```

### Scheduling Integration

#### Modified TaskSchedule Class:
```python
class TaskSchedule:
    def __init__(self, ..., burst_enabled=False, burst_config=None):
        # Initialize burst management if enabled
        if burst_enabled:
            self.burst_manager = BurstTaskManager(...)
            self.burst_scheduler = BurstAwareTaskScheduler(...)
```

#### Runtime Burst Management:
```python
def distribute_tasks(self):
    # ... existing distribution logic ...
    
    # Apply burst-aware scheduling to putback tasks
    if self.burst_enabled and self.burst_scheduler:
        remaining_tasks, dropped_tasks = self.burst_scheduler.burst_manager.proactive_drop(putback, current_time)
        # Handle dropped tasks
        for dropped_task in dropped_tasks:
            self.handle_dropped_task(dropped_task.get('TaskId', 'Unknown'))
```

## Monitoring and Statistics

### Burst Statistics
The system provides comprehensive burst management statistics:
```python
{
    "burst_mode_active": bool,
    "dropped_tasks_count": int,
    "current_gpu_utilization": float,
    "current_queue_length": int,
    "gpu_threshold": float,
    "queue_threshold": int
}
```

### Logging
Burst management events are logged with `[BURST]` prefix:
- Overload detection and resolution
- Task dropping decisions
- Criticality score calculations
- System health metrics

## Performance Considerations

### Monitoring Overhead
- GPU monitoring interval: 100ms (configurable)
- Minimal CPU overhead for health monitoring
- Asynchronous monitoring thread

### Task Dropping Efficiency
- O(n log n) complexity for criticality sorting
- Individual task drop thresholds for fine-grained control
- Configurable drop percentages

### Memory Usage
- Minimal additional memory for burst management
- Efficient task statistics tracking
- Cleanup of dropped task references

## Testing and Validation

### Test Scenarios
1. **Normal Operation**: System under normal load
2. **Overload Detection**: GPU utilization above threshold
3. **Task Dropping**: Proactive task dropping under overload
4. **Recovery**: System recovery after overload resolution

### Validation Metrics
- Task completion rates
- Deadline miss rates
- System responsiveness
- Resource utilization

## Future Enhancements

### Potential Improvements
1. **Adaptive Thresholds**: Dynamic threshold adjustment based on historical data
2. **Machine Learning**: ML-based criticality prediction
3. **Multi-GPU Support**: Extension to multi-GPU environments
4. **Advanced Metrics**: Additional system health indicators

### Integration Opportunities
1. **Container Orchestration**: Integration with Kubernetes/Docker
2. **Cloud Platforms**: AWS, Azure, GCP integration
3. **Edge Computing**: IoT and edge device support

## Troubleshooting

### Common Issues
1. **GPU Monitoring Not Available**: Falls back to 0% utilization
2. **High Drop Rates**: Adjust thresholds in burst configuration
3. **Performance Impact**: Reduce monitoring interval

### Debug Information
- Enable debug logging for detailed burst management information
- Monitor burst statistics for system health
- Check task criticality scores for unexpected behavior

## Conclusion

The burst task management implementation provides a robust solution for handling dynamic workload patterns in real-time deep learning systems. The proactive task dropping mechanism ensures system stability while preserving high-priority tasks, making it suitable for production deployment scenarios. 