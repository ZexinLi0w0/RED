import time
import math
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import subprocess
import threading
import queue

class SystemHealthMonitor:
    """
    Monitors system health indicators including GPU utilization, queue length, and deadline slack.
    """
    
    def __init__(self, logger=None, monitoring_interval: float = 0.1):
        self.logger = logger or logging.getLogger(__name__)
        self.gpu_utilization = 0.0
        self.queue_length = 0
        self.monitoring_active = False
        self.monitor_thread = None
        self.monitoring_interval = max(0.02, float(monitoring_interval))
        
    def start_monitoring(self):
        """Start the system health monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("[BURST] System health monitoring started")
    
    def stop_monitoring(self):
        """Stop the system health monitoring thread."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.logger.info("[BURST] System health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop that continuously updates system health metrics."""
        while self.monitoring_active:
            try:
                # Update GPU utilization
                self.gpu_utilization = self._get_gpu_utilization()
                self.logger.debug(f"[BURST][HEALTH] GPU utilization: {self.gpu_utilization:.1f}%")
                
                # Sleep for a short interval before next measurement
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"[BURST] Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _get_gpu_utilization(self) -> float:
        """
        Get current GPU utilization percentage.
        Returns 0.0 if GPU monitoring is not available.
        """
        try:
            # Try to get GPU utilization using nvidia-smi
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        
        # Fallback: try tegrastats for Jetson devices
        try:
            result = subprocess.run(
                ["tegrastats", "--readall"],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                return self._parse_tegrastats_gpu(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return 0.0
    
    def _parse_tegrastats_gpu(self, stats_output: str) -> float:
        """Parse GPU utilization from tegrastats output."""
        try:
            # Look for GR3D_FREQ pattern in tegrastats output
            if "GR3D_FREQ" in stats_output:
                parts = stats_output.split("GR3D_FREQ", 1)
                if len(parts) > 1:
                    gpu_part = parts[1].split()[0]
                    return float(gpu_part.replace("%", ""))
        except (ValueError, IndexError):
            pass
        return 0.0
    
    def get_system_health(self) -> Dict[str, float]:
        """Get current system health metrics."""
        return {
            "gpu_utilization": self.gpu_utilization,
            "queue_length": self.queue_length
        }
    
    def update_queue_length(self, length: int):
        """Update the current queue length."""
        self.queue_length = length

class BurstTaskManager:
    """
    Manages burst task scenarios with proactive task dropping mechanism.
    """
    
    def __init__(self, 
                 gpu_threshold: float = 80.0,
                 queue_threshold: int = 10,
                 default_drop_threshold: float = 0.5,
                 monitoring_interval: float = 0.1,
                 logger=None):
        self.gpu_threshold = gpu_threshold
        self.queue_threshold = queue_threshold
        self.default_drop_threshold = default_drop_threshold
        self.logger = logger or logging.getLogger(__name__)
        self.health_monitor = SystemHealthMonitor(logger, monitoring_interval=monitoring_interval)
        self.dropped_tasks = []
        self.burst_mode_active = False
        
    def start_monitoring(self):
        """Start the burst task monitoring."""
        self.health_monitor.start_monitoring()
    
    def stop_monitoring(self):
        """Stop the burst task monitoring."""
        self.health_monitor.stop_monitoring()
    
    def calculate_criticality_score(self, task: Dict, current_time: float) -> float:
        """
        Calculate the criticality score for a task.
        
        Criticality score formula per spec: C_i = 1 - (S_i / D_i)
        where S_i = D_i - t is the slack time, D_i is the relative intermediate deadline,
        and t is the elapsed time since task release.
        
        Args:
            task: Task dictionary containing deadline and other attributes
            current_time: Current time since task start
            
        Returns:
            Criticality score (higher = more critical)
        """
        try:
            # Here current_time is expected to be relative to TaskStartTime
            deadline = float(task.get("Deadline", 0.0))       # relative to TaskStartTime
            release_time = float(task.get("ReleaseTime", 0.0)) # relative to TaskStartTime

            # Relative intermediate deadline duration D_i
            relative_deadline = deadline - release_time
            if relative_deadline <= 0:
                return 0.0
            
            # Elapsed time since release t (non-negative)
            elapsed_time = max(0.0, current_time - release_time)

            # Slack S_i = D_i - t
            slack_time = relative_deadline - elapsed_time

            # C_i = 1 - (S_i / D_i)
            criticality = 1.0 - (slack_time / relative_deadline)
            # Clamp between 0 and 1
            criticality = max(0.0, min(1.0, criticality))
            return criticality
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"[BURST] Error calculating criticality score: {e}")
            return 0.0
    
    def is_overload_detected(self) -> bool:
        """
        Check if system overload is detected based on health metrics.
        
        Returns:
            True if overload detected, False otherwise
        """
        health = self.health_monitor.get_system_health()
        gpu_util = health.get("gpu_utilization", 0.0)
        queue_len = health.get("queue_length", 0)
        
        overload = (gpu_util > self.gpu_threshold or queue_len > self.queue_threshold)
        
        if overload and not self.burst_mode_active:
            self.logger.warning(f"[BURST] Overload detected: GPU={gpu_util:.1f}%, Queue={queue_len}")
            self.burst_mode_active = True
        elif not overload and self.burst_mode_active:
            self.logger.info(f"[BURST] Overload resolved: GPU={gpu_util:.1f}%, Queue={queue_len}")
            self.burst_mode_active = False
        
        return overload
    
    def proactive_drop(self, task_queue: List[Dict], current_time: float) -> Tuple[List[Dict], List[Dict]]:
        """
        Implement proactive task dropping algorithm.
        
        Args:
            task_queue: List of tasks in the queue
            current_time: Current time since system start
            
        Returns:
            Tuple of (remaining_tasks, dropped_tasks)
        """
        if not self.is_overload_detected():
            return task_queue, []
        
        # Calculate criticality scores for all tasks
        # [TODO] This can be optimized by priority queue or min heap
        tasks_with_scores = []
        for task in task_queue:
            criticality = self.calculate_criticality_score(task, current_time)
            tasks_with_scores.append((task, criticality))
        
        # Sort tasks by criticality score (ascending - lower scores dropped first)
        tasks_with_scores.sort(key=lambda x: x[1])
        
        # Determine how many tasks to drop based on individual drop thresholds
        dropped_tasks = []
        remaining_tasks = []
        
        for task, criticality in tasks_with_scores:
            drop_threshold = float(task.get("DropThreshold", self.default_drop_threshold))
            
            # Drop task if its criticality is below its drop threshold
            if criticality < drop_threshold:
                dropped_tasks.append(task)
                self.logger.info(f"[BURST] Dropped task {task.get('TaskId', 'Unknown')} "
                               f"with criticality {criticality:.3f} (threshold: {drop_threshold:.3f})")
            else:
                remaining_tasks.append(task)
        
        self.dropped_tasks.extend(dropped_tasks)
        if len(dropped_tasks) > 0:
            self.logger.info(f"[BURST] Dropped {len(dropped_tasks)} tasks, "
                        f"remaining {len(remaining_tasks)} tasks")
        
        return remaining_tasks, dropped_tasks
    
    def get_burst_statistics(self) -> Dict:
        """Get statistics about burst management."""
        return {
            "burst_mode_active": self.burst_mode_active,
            "dropped_tasks_count": len(self.dropped_tasks),
            "current_gpu_utilization": self.health_monitor.gpu_utilization,
            "current_queue_length": self.health_monitor.queue_length,
            "gpu_threshold": self.gpu_threshold,
            "queue_threshold": self.queue_threshold
        }
    
    def update_queue_length(self, length: int):
        """Update the current queue length for monitoring."""
        self.health_monitor.update_queue_length(length)

class BurstAwareTaskScheduler:
    """
    Task scheduler that integrates burst task management.
    """
    
    def __init__(self, 
                 burst_manager: BurstTaskManager,
                 base_scheduler,
                 logger=None):
        self.burst_manager = burst_manager
        self.base_scheduler = base_scheduler
        self.logger = logger or logging.getLogger(__name__)
        
    def schedule_tasks(self, task_queue: List[Dict], current_time: float) -> Tuple[List[Dict], List[Dict]]:
        """
        Schedule tasks with burst awareness.
        
        Args:
            task_queue: List of tasks to schedule
            current_time: Current time since system start
            
        Returns:
            Tuple of (scheduled_tasks, dropped_tasks)
        """
        # Update queue length for monitoring
        self.burst_manager.update_queue_length(len(task_queue))
        
        # Check for burst conditions and apply proactive dropping
        remaining_tasks, dropped_tasks = self.burst_manager.proactive_drop(task_queue, current_time)
        
        # Apply base scheduler to remaining tasks
        scheduled_tasks = remaining_tasks.copy()
        
        # Apply sorting based on scheduler type
        if self.base_scheduler == 'edf':
            # Sort by deadline (EDF)
            scheduled_tasks.sort(key=lambda x: x.get("Deadline", 0))
        elif self.base_scheduler == 'priority':
            # Sort by priority (descending)
            scheduled_tasks.sort(key=lambda x: x.get("Priority", 0), reverse=True)
        elif self.base_scheduler == 'fcfs':
            # Sort by release time (FCFS)
            scheduled_tasks.sort(key=lambda x: x.get("ReleaseTime", 0))
        elif self.base_scheduler == 'fcls':
            # Sort by release time (descending) (FCLS)
            scheduled_tasks.sort(key=lambda x: x.get("ReleaseTime", 0), reverse=True)
        
        return scheduled_tasks, dropped_tasks
    
    def get_burst_statistics(self) -> Dict:
        """Get burst management statistics."""
        return self.burst_manager.get_burst_statistics() 