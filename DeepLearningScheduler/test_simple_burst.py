#!/usr/bin/env python3
"""
Simple test to isolate and fix the burst task scheduling issue.
"""

import time
import logging
from collections import defaultdict
from task_generator import load_task_config, generate_tasks
from task_scheduler import TaskSchedule

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_simple_burst():
    """Simple test to isolate the burst task issue."""
    logger = setup_logging()
    logger.info("Testing Simple Burst Task Management...")
    
    try:
        # Load task configuration
        task_config = load_task_config("TaskConfigs/burst-task-config.json")
        if task_config is None:
            logger.error("Failed to load task configuration")
            return
        
        tasks = generate_tasks(task_config)
        logger.info(f"Generated {len(tasks)} tasks")
        
        # Create task scheduler WITHOUT burst management first
        handler_status = defaultdict(lambda: 1)  # All handlers ready
        task_scheduler = TaskSchedule(
            tasks=tasks,
            handler_status=handler_status,
            control_queue=[],
            scheduler='edf',
            logger=logger,
            approach_module='baseline',
            task_filename='burst-test',
            burst_enabled=False  # Disable burst for now
        )
        
        # Generate task list
        task_scheduler.generate_task_list()
        logger.info(f"Task queue length: {len(task_scheduler.TaskQueue)}")
        logger.info("Basic task scheduling works!")
        
        # Now test with burst enabled
        task_scheduler_burst = TaskSchedule(
            tasks=tasks,
            handler_status=handler_status,
            control_queue=[],
            scheduler='edf',
            logger=logger,
            approach_module='baseline',
            task_filename='burst-test',
            burst_enabled=True,
            burst_config={
                "burst_enabled": True,
                "gpu_threshold": 75.0,
                "queue_threshold": 8
            }
        )
        
        # Generate task list with burst
        task_scheduler_burst.generate_task_list()
        logger.info(f"Burst task queue length: {len(task_scheduler_burst.TaskQueue)}")
        logger.info("Burst task scheduling works!")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_burst() 