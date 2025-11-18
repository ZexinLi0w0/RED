#!/usr/bin/env python3

from task_generator import load_dag_config, generate_tasks_from_dag

def test_non_partitionable_tasks():
    """Test the non-partitionable tasks feature"""
    print("Testing Non-Partitionable Tasks Feature...")
    
    # Load the test configuration
    result = load_dag_config('TaskConfigs/simo/test_non_partitionable.json')
    if result is None:
        print("Error: Failed to load DAG config")
        return False
    
    dag_config, factor, non_partitionable_percentage, non_partitionable_config, _ = result
    print(f"Configuration loaded:")
    print(f"  RunningTimeFactor: {factor}")
    print(f"  NonPartitionablePercentage: {non_partitionable_percentage}%")
    print(f"  NonPartitionableConfig: {non_partitionable_config}")
    
    # Generate tasks
    tasks = generate_tasks_from_dag(dag_config, time_factor=factor, 
                                   non_partitionable_percentage=non_partitionable_percentage, 
                                   non_partitionable_config=non_partitionable_config)
    
    print(f"\nTask Generation Results:")
    print(f"  Total tasks: {len(tasks)}")
    
    # Count non-partitionable tasks
    non_partitionable_count = sum(1 for task in tasks if task.get('IsNonPartitionable', False))
    partitionable_count = len(tasks) - non_partitionable_count
    
    print(f"  Non-partitionable tasks: {non_partitionable_count}")
    print(f"  Partitionable tasks: {partitionable_count}")
    print(f"  Actual percentage: {non_partitionable_count/len(tasks)*100:.1f}%")
    
    # Show some example tasks
    print(f"\nExample tasks:")
    for i, task in enumerate(tasks[:5]):
        print(f"  Task {i+1}: {task['TaskId']} - Non-partitionable: {task.get('IsNonPartitionable', False)}")
    
    # Verify the feature is working
    expected_percentage = non_partitionable_percentage
    actual_percentage = non_partitionable_count / len(tasks) * 100
    tolerance = 5  # Allow 5% tolerance due to random selection
    
    if abs(actual_percentage - expected_percentage) <= tolerance:
        print(f"\n✅ SUCCESS: Non-partitionable tasks feature is working correctly!")
        print(f"   Expected: {expected_percentage}%, Actual: {actual_percentage:.1f}%")
        return True
    else:
        print(f"\n❌ FAILED: Non-partitionable tasks feature is not working correctly!")
        print(f"   Expected: {expected_percentage}%, Actual: {actual_percentage:.1f}%")
        return False

if __name__ == "__main__":
    test_non_partitionable_tasks() 