#!/usr/bin/env python3
"""
Test script for burst task management functionality.
This script demonstrates how the burst task system works with different scenarios.
"""

import time
import json
import logging
from task_generator import load_task_config, generate_tasks
from task_scheduler import TaskSchedule
from burst_task_manager import BurstTaskManager, SystemHealthMonitor
from collections import defaultdict

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_burst_task_manager():
    """Test the burst task manager functionality."""
    logger = setup_logging()
    logger.info("Testing Burst Task Manager...")
    
    # Create burst task manager
    burst_manager = BurstTaskManager(
        gpu_threshold=70.0,
        queue_threshold=5,
        logger=logger
    )
    
    # Start monitoring
    burst_manager.start_monitoring()
    
    # Create sample tasks
    tasks = [
        {
            "TaskId": "task_1",
            "HandlerId": 5,
            "ReleaseTime": 0.0,
            "Deadline": 0.01,
            "Priority": 1,
            "BurstPriority": 2,
            "CriticalityWeight": 1.5,
            "DropThreshold": 0.3
        },
        {
            "TaskId": "task_2", 
            "HandlerId": 5,
            "ReleaseTime": 0.5,
            "Deadline": 0.015,
            "Priority": 2,
            "BurstPriority": 1,
            "CriticalityWeight": 1.0,
            "DropThreshold": 0.6
        },
        {
            "TaskId": "task_3",
            "HandlerId": 5,
            "ReleaseTime": 1.0,
            "Deadline": 0.02,
            "Priority": 3,
            "BurstPriority": 3,
            "CriticalityWeight": 2.0,
            "DropThreshold": 0.2
        }
    ]
    
    # Test criticality score calculation
    current_time = time.time()
    for task in tasks:
        criticality = burst_manager.calculate_criticality_score(task, current_time)
        logger.info(f"Task {task['TaskId']}: criticality = {criticality:.3f}")
    
    # Test proactive drop
    remaining_tasks, dropped_tasks = burst_manager.proactive_drop(tasks, current_time)
    logger.info(f"Remaining tasks: {len(remaining_tasks)}")
    logger.info(f"Dropped tasks: {len(dropped_tasks)}")
    
    # Stop monitoring
    burst_manager.stop_monitoring()
    
    # Get final statistics
    stats = burst_manager.get_burst_statistics()
    logger.info(f"Burst statistics: {stats}")

def test_burst_drop_due_to_gpu():
    """Test that GPU over-utilization triggers proactive dropping of low-criticality tasks."""
    logger = setup_logging()
    logger.info("Testing Burst Drop due to GPU Over-Utilization...")

    # Create burst task manager with low GPU threshold to ensure overload triggers
    burst_manager = BurstTaskManager(
        gpu_threshold=50.0,   # any value below mocked GPU util
        queue_threshold=1000, # keep queue impact out of the test
        logger=logger
    )

    # Mock system health to simulate high GPU utilization
    burst_manager.health_monitor.get_system_health = lambda: {"gpu_utilization": 95.0, "queue_length": 0}

    # Prepare tasks with varying criticality (relative time frame)
    # C = t/D. With drop_threshold=0.5, tasks with C < 0.5 will be dropped
    tasks = [
        {"TaskId": "gpu_task_1", "HandlerId": 5, "ReleaseTime": 0.0, "Deadline": 1.0, "Priority": 1},  # t/D=0.2 -> drop
        {"TaskId": "gpu_task_2", "HandlerId": 5, "ReleaseTime": 0.0, "Deadline": 1.0, "Priority": 1},  # t/D=0.2 -> drop
        {"TaskId": "gpu_task_3", "HandlerId": 5, "ReleaseTime": 0.0, "Deadline": 1.0, "Priority": 1},  # t/D=0.8 -> keep
    ]

    # Current time relative to TaskStartTime
    low_t = 0.2
    high_t = 0.8

    # First two tasks evaluated at low_t, last one at high_t
    remaining_1, dropped_1 = burst_manager.proactive_drop(tasks[:2], low_t)
    remaining_2, dropped_2 = burst_manager.proactive_drop(tasks[2:], high_t)

    dropped_total = len(dropped_1) + len(dropped_2)
    kept_total = len(remaining_1) + len(remaining_2)

    logger.info(f"GPU-drop test: dropped={dropped_total}, kept={kept_total}")
    # Expect at least one drop due to GPU overload and low criticality
    assert dropped_total >= 1

def test_task_scheduler_with_burst():
    """Test the task scheduler with burst management enabled."""
    logger = setup_logging()
    logger.info("Testing Task Scheduler with Burst Management...")
    
    # Load burst configuration
    burst_config = {
        "burst_enabled": True,
        "gpu_threshold": 75.0,
        "queue_threshold": 8,
        "drop_percentage": 25,
        "monitoring_interval": 0.1,
        "criticality_weight": 1.0
    }
    
    # Load task configuration
    try:
        task_config = load_task_config("TaskConfigs/burst-task-config.json")
        if task_config is None:
            logger.error("Failed to load task configuration")
            return
        
        tasks = generate_tasks(task_config)
        logger.info(f"Generated {len(tasks)} tasks")
        
        # Create task scheduler with burst management
        handler_status = defaultdict(lambda: 1)  # All handlers ready
        task_scheduler = TaskScthedule(
            tasks=tasks,
            handler_status=handler_status,
            control_queue=[],
            scheduler='edf',
            logger=logger,
            approach_module='baseline',
            task_filename='burst-test',
            burst_enabled=True,
            burst_config=burst_config
        )
        
        # Generate task list
        task_scheduler.generate_task_list()
        logger.info(f"Task queue length: {len(task_scheduler.TaskQueue)}")
        
        # Simulate task distribution
        for i in range(5):
            logger.info(f"Distribution round {i+1}")
            continue_distribution = task_scheduler.distribute_tasks()
            if not continue_distribution:
                break
            time.sleep(0.1)
        
        # Get burst statistics
        if task_scheduler.burst_manager:
            stats = task_scheduler.burst_manager.get_burst_statistics()
            logger.info(f"Final burst statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")

def test_system_health_monitor():
    """Test the system health monitor."""
    logger = setup_logging()
    logger.info("Testing System Health Monitor...")
    
    # Create health monitor
    health_monitor = SystemHealthMonitor(logger=logger)
    
    # Start monitoring
    health_monitor.start_monitoring()
    
    # Monitor for a few seconds
    for i in range(10):
        health = health_monitor.get_system_health()
        logger.info(f"Health metrics: GPU={health['gpu_utilization']:.1f}%, Queue={health['queue_length']}")
        time.sleep(0.5)
    
    # Stop monitoring
    health_monitor.stop_monitoring()

def main():
    """Main test function."""
    logger = setup_logging()
    logger.info("Starting Burst Task Management Tests...")
    
    try:
        # Test system health monitor
        test_system_health_monitor()
        
        # Test burst task manager
        test_burst_task_manager()
        # Test GPU-overload-driven dropping
        test_burst_drop_due_to_gpu()
        
        # Test task scheduler with burst management
        test_task_scheduler_with_burst()
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    main() 